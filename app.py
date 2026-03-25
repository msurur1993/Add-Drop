import atexit
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from sqlite3 import IntegrityError as SQLiteIntegrityError
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from apscheduler.schedulers.background import BackgroundScheduler
from authlib.integrations.base_client import OAuthError
from authlib.integrations.flask_client import OAuth
from flask import Flask, flash, make_response, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from departments import DEPARTMENTS
from models import ClassStatus, Notification, User, WatchedClass, db
from notifier import (
    _email_settings,
    _send_via_resend,
    _send_via_smtp,
    _send_via_gmail,
    notification_provider_name,
    notification_sender,
    notifications_ready,
    notify_user,
)
from scraper import PeopleSoftScraper

_is_production = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PRODUCTION"))
if _is_production:
    from pythonjsonlogger import jsonlogger
    _handler = logging.StreamHandler()
    _handler.setFormatter(jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    ))
    logging.root.handlers = [_handler]
    logging.root.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MAX_WATCHES_PER_USER = 5
MAX_CONSECUTIVE_FAILURES = int(os.environ.get("MAX_SCRAPER_FAILURES", "5"))
ALERT_COOLDOWN_SECONDS = 3600  # Max 1 admin alert per hour

# --- Scheduler health tracking ---
_scheduler_state = {
    "consecutive_failures": 0,
    "last_successful_check": None,
    "last_alert_time": None,
}

# --- App setup ---
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

CHICAGO_TZ = ZoneInfo("America/Chicago")


@app.template_filter("chicago_time")
def chicago_time_filter(dt):
    """Convert a UTC datetime to Chicago time, formatted as 12-hour."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CHICAGO_TZ).strftime("%-I:%M %p")


def google_oauth_ready():
    return bool(app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"])


def build_unique_username(email, name):
    base = (email.split("@")[0] if email else (name or "user")).strip().lower()
    base = re.sub(r"[^a-z0-9._-]+", "", base) or "user"

    candidate = base
    suffix = 1
    while User.query.filter_by(username=candidate).first():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def build_unique_ntfy_topic(email, name):
    base = (email.split("@")[0] if email else (name or "user")).strip().lower()
    base = re.sub(r"[^a-z0-9._-]+", "-", base).strip("-") or "user"

    while True:
        candidate = f"addrop-{base}-{secrets.token_hex(6)}"
        if not User.query.filter_by(ntfy_topic=candidate).first():
            return candidate


# --- Google OAuth ---
oauth = OAuth(app)
google = None
if google_oauth_ready():
    google = oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url=app.config["GOOGLE_DISCOVERY_URL"],
        client_kwargs={"scope": "openid email profile"},
    )
else:
    logger.warning(
        "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
    )

# --- Scraper ---
scraper = PeopleSoftScraper({
    "PEOPLESOFT_URL": app.config["PEOPLESOFT_URL"],
    "PLAYWRIGHT_HEADLESS": app.config["PLAYWRIGHT_HEADLESS"],
})

# --- Scheduler ---
scheduler = BackgroundScheduler()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.headers.get("HX-Request"):
                resp = make_response("", 200)
                resp.headers["HX-Redirect"] = url_for("index")
                return resp
            return redirect(url_for("index"))
        user = db.session.get(User, session["user_id"])
        if not user:
            session.clear()
            if request.headers.get("HX-Request"):
                resp = make_response("", 200)
                resp.headers["HX-Redirect"] = url_for("index")
                return resp
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


# --- Routes ---

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login/google")
@limiter.limit("5/minute")
def login_google():
    if not google:
        flash("Google sign-in is not configured yet.", "error")
        return redirect(url_for("index"))

    redirect_uri = app.config["GOOGLE_OAUTH_REDIRECT_URI"] or url_for(
        "google_callback",
        _external=True,
    )
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def google_callback():
    if not google:
        flash("Google sign-in is not configured yet.", "error")
        return redirect(url_for("index"))

    try:
        token = google.authorize_access_token()
    except OAuthError as exc:
        logger.warning("Google OAuth callback failed: %s", exc)
        flash("Google sign-in failed. Please try again.", "error")
        return redirect(url_for("index"))

    user_info = token.get("userinfo")
    if not user_info:
        response = google.get("userinfo", token=token)
        user_info = response.json() if response else None
    if not user_info:
        flash("Could not get your Google account info.", "error")
        return redirect(url_for("index"))

    google_id = user_info["sub"]
    email = user_info.get("email", "")
    name = user_info.get("name", email.split("@")[0])

    user = User.query.filter_by(google_id=google_id).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            google_id=google_id,
            email=email or None,
            name=name or None,
            username=build_unique_username(email, name),
            ntfy_topic=build_unique_ntfy_topic(email, name),
        )
        db.session.add(user)
        db.session.commit()
    else:
        changed = False
        if user.google_id != google_id:
            user.google_id = google_id
            changed = True
        if email and user.email != email:
            user.email = email
            changed = True
        if name and user.name != name:
            user.name = name
            changed = True
        if not user.ntfy_topic:
            user.ntfy_topic = build_unique_ntfy_topic(email or user.email, name or user.name)
            changed = True
        if changed:
            db.session.commit()

    # Regenerate session to prevent fixation
    session.clear()
    session["user_id"] = user.id
    session["username"] = user.name or user.username
    logger.info("User signed in", extra={"event": "user_signin", "user_id": user.id, "email": email})
    flash("Signed in with Google.", "success")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = db.session.get(User, session["user_id"])
    watches = WatchedClass.query.filter_by(user_id=user.id).order_by(WatchedClass.created_at.desc()).all()

    # Get watcher counts for tracked classes
    from sqlalchemy import func as sa_func
    count_query = (
        db.session.query(
            WatchedClass.subject, WatchedClass.catalog_number, WatchedClass.section,
            sa_func.count(WatchedClass.id).label("cnt"),
        )
        .filter(WatchedClass.term.in_([w.term for w in watches]))
        .group_by(WatchedClass.subject, WatchedClass.catalog_number, WatchedClass.section)
        .all()
    ) if watches else []
    watcher_counts = {(s, c, sec): cnt for s, c, sec, cnt in count_query}

    watch_data = []
    for w in watches:
        status = ClassStatus.query.filter_by(
            subject=w.subject, catalog_number=w.catalog_number,
            section=w.section, term=w.term
        ).first()
        wc = watcher_counts.get((w.subject, w.catalog_number, w.section), 0)
        watch_data.append({"watch": w, "status": status, "watcher_count": wc})

    return render_template(
        "dashboard.html",
        user=user,
        watch_data=watch_data,
        watch_count=len(watches),
        term=app.config["CURRENT_TERM"],
        departments=DEPARTMENTS,
        notifications_ready=notifications_ready(app.config),
    )


CACHE_MAX_AGE_SECONDS = 120  # Serve cached results if less than 2 minutes old


@app.route("/search", methods=["POST"])
@limiter.limit("10/minute")
@login_required
def search():
    subject = request.form.get("subject", "").strip().upper()
    keyword = request.form.get("keyword", "").strip()
    term = app.config["CURRENT_TERM"]

    if not keyword:
        return render_template("partials/search_results.html", results=[], error="Enter a course name, number, or instructor.")

    # Try to serve from DB cache first (avoids Playwright for repeated searches)
    results = None
    cache_cutoff = datetime.now(timezone.utc) - timedelta(seconds=CACHE_MAX_AGE_SECONDS)

    if subject:
        # Exact department + keyword search: check if we have fresh cached results
        cached = ClassStatus.query.filter(
            ClassStatus.subject == subject,
            ClassStatus.catalog_number.contains(keyword),
            ClassStatus.term == term,
            ClassStatus.last_checked >= cache_cutoff,
        ).all()
        if not cached:
            # Also try matching by course name
            cached = ClassStatus.query.filter(
                ClassStatus.subject == subject,
                ClassStatus.course_name.ilike(f"%{keyword}%"),
                ClassStatus.term == term,
                ClassStatus.last_checked >= cache_cutoff,
            ).all()
        if cached:
            results = [
                {
                    "subject": cs.subject, "catalog_number": cs.catalog_number,
                    "section": cs.section, "course_name": cs.course_name or "",
                    "course_id": f"{cs.subject} {cs.catalog_number}/{cs.section}",
                    "class_nbr": cs.class_nbr or "", "enrolled": cs.enrolled,
                    "capacity": cs.capacity, "status": cs.status,
                    "instructor": cs.instructor or "", "schedule": cs.schedule or "",
                }
                for cs in cached
            ]
            logger.info(f"Cache hit: {len(results)} results for {subject} '{keyword}'")

    # Cache miss — scrape PeopleSoft
    if results is None:
        results = scraper.search_class(term, subject, keyword)

        now = datetime.now(timezone.utc)
        for r in results:
            r_subject = r.get("subject", subject)
            r_catalog = r.get("catalog_number", keyword)
            cs = ClassStatus.query.filter_by(
                subject=r_subject, catalog_number=r_catalog,
                section=r["section"], term=term
            ).first()
            if cs:
                cs.course_name = r["course_name"]
                cs.enrolled = r["enrolled"]
                cs.capacity = r["capacity"]
                cs.instructor = r.get("instructor", "")
                cs.schedule = r.get("schedule", "")
                cs.class_nbr = r.get("class_nbr", "")
                if cs.status != r["status"]:
                    cs.last_changed = now
                cs.status = r["status"]
                cs.last_checked = now
            else:
                cs = ClassStatus(
                    subject=r_subject, catalog_number=r_catalog,
                    section=r["section"], term=term,
                    course_name=r["course_name"], enrolled=r["enrolled"],
                    capacity=r["capacity"], status=r["status"],
                    instructor=r.get("instructor", ""),
                    schedule=r.get("schedule", ""),
                    class_nbr=r.get("class_nbr", ""),
                    last_checked=now, last_changed=now,
                )
                db.session.add(cs)
        db.session.commit()

    user_id = session["user_id"]
    watched_keys = set()
    for w in WatchedClass.query.filter_by(user_id=user_id, term=term).all():
        watched_keys.add((w.subject, w.catalog_number, w.section))

    # Count how many users are tracking each class in the results
    watcher_counts = {}
    if results:
        from sqlalchemy import func
        keys = [(r.get("subject", ""), r.get("catalog_number", ""), r.get("section", "")) for r in results]
        counts = (
            db.session.query(
                WatchedClass.subject, WatchedClass.catalog_number, WatchedClass.section,
                func.count(WatchedClass.id).label("cnt"),
            )
            .filter(WatchedClass.term == term)
            .group_by(WatchedClass.subject, WatchedClass.catalog_number, WatchedClass.section)
            .all()
        )
        for subj, cat, sec, cnt in counts:
            watcher_counts[(subj, cat, sec)] = cnt

    return render_template(
        "partials/search_results.html",
        results=results, term=term, watched_keys=watched_keys,
        watcher_counts=watcher_counts, error=None,
    )


@app.route("/watch", methods=["POST"])
@limiter.limit("20/minute")
@login_required
def watch():
    user_id = session["user_id"]
    subject = request.form.get("subject", "").strip().upper()
    catalog_number = request.form.get("catalog_number", "").strip()
    section = request.form.get("section", "").strip()
    term = request.form.get("term", "").strip()

    # Don't allow tracking classes that are already open
    cs = ClassStatus.query.filter_by(
        subject=subject, catalog_number=catalog_number, section=section, term=term
    ).first()
    if cs and cs.status == "Open":
        toast = (
            '<div hx-swap-oob="afterbegin:#toast-area">'
            '<div class="toast bg-emerald-50 text-emerald-700 border border-emerald-200">'
            f'{subject} {catalog_number} is open — go enroll now!</div></div>'
        )
        return make_response(toast, 200)

    existing = WatchedClass.query.filter_by(
        user_id=user_id, subject=subject, catalog_number=catalog_number,
        section=section, term=term
    ).first()
    if not existing:
        current_count = WatchedClass.query.filter_by(user_id=user_id).count()
        if current_count >= MAX_WATCHES_PER_USER:
            toast = (
                '<div hx-swap-oob="afterbegin:#toast-area">'
                '<div class="toast bg-red-50 text-red-700 border border-red-200">'
                f'Limit reached: you can track up to {MAX_WATCHES_PER_USER} classes.</div></div>'
            )
            return make_response(toast, 200)
        wc = WatchedClass(user_id=user_id, subject=subject, catalog_number=catalog_number, section=section, term=term)
        db.session.add(wc)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            existing = WatchedClass.query.filter_by(
                user_id=user_id, subject=subject, catalog_number=catalog_number,
                section=section, term=term
            ).first()

    status = ClassStatus.query.filter_by(
        subject=subject, catalog_number=catalog_number, section=section, term=term
    ).first()

    w = existing or wc
    new_count = WatchedClass.query.filter_by(user_id=user_id).count()
    logger.info("Class tracked", extra={"event": "class_tracked", "user_id": user_id, "class": f"{subject} {catalog_number} Sec {section}"})

    # Count how many users are tracking this class
    from sqlalchemy import func as sa_func
    watcher_count = WatchedClass.query.filter_by(
        subject=subject, catalog_number=catalog_number, section=section, term=term
    ).count()

    btn_id = f"track-btn-{subject}-{catalog_number}-{section}"
    watchlist_html = render_template("partials/watchlist_item.html", watch=w, status=status, watcher_count=watcher_count)
    oob_html = f'<span id="{btn_id}" hx-swap-oob="true" class="text-xs text-gray-400 px-3 py-1.5 bg-gray-100 rounded-lg">Tracking</span>'
    counter_html = f'<span id="slot-counter" hx-swap-oob="true" class="text-xs text-gray-400">{new_count}/5 slots used</span>'
    # Remove the "No classes tracked yet" empty state
    empty_html = '<p id="empty-watchlist" hx-swap-oob="true"></p>'
    toast_html = (
        '<div hx-swap-oob="afterbegin:#toast-area">'
        f'<div class="toast bg-green-50 text-green-700 border border-green-200">'
        f'Now tracking {subject} {catalog_number} Sec {section}</div></div>'
    )

    resp = make_response(watchlist_html + oob_html + counter_html + empty_html + toast_html)
    return resp


@app.route("/unwatch/<int:watch_id>", methods=["DELETE"])
@login_required
def unwatch(watch_id):
    wc = WatchedClass.query.filter_by(id=watch_id, user_id=session["user_id"]).first()
    if wc:
        subject = wc.subject
        catalog_number = wc.catalog_number
        section = wc.section
        term = wc.term
        label = f"{subject} {catalog_number} Sec {section}"
        db.session.delete(wc)
        db.session.commit()
        logger.info("Class untracked", extra={"event": "class_untracked", "user_id": session["user_id"], "class": label})
        new_count = WatchedClass.query.filter_by(user_id=session["user_id"]).count()

        counter_html = f'<span id="slot-counter" hx-swap-oob="true" class="text-xs text-gray-400">{new_count}/5 slots used</span>'
        # Revert "Tracking" label back to a "Track" button in search results
        btn_id = f"track-btn-{subject}-{catalog_number}-{section}"
        btn_html = (
            f'<button id="{btn_id}" hx-swap-oob="true"'
            f' hx-post="/watch"'
            f""" hx-vals='{{"subject": "{subject}", "catalog_number": "{catalog_number}", "section": "{section}", "term": "{term}"}}'"""
            f' hx-target="#watchlist" hx-swap="afterbegin"'
            f' class="text-xs px-3 py-1.5 bg-[#800000] hover:bg-[#9A2A2A] text-white rounded-lg transition">'
            f'Track</button>'
        )
        # Show empty state if watchlist is now empty
        empty_html = ""
        if new_count == 0:
            empty_html = '<p id="empty-watchlist" hx-swap-oob="true" class="text-gray-400 text-sm">No classes tracked yet. Search and add classes to start monitoring.</p>'
        toast_html = (
            '<div hx-swap-oob="afterbegin:#toast-area">'
            f'<div class="toast bg-gray-50 text-gray-700 border border-gray-200">'
            f'Removed {label} from watchlist</div></div>'
        )
        return make_response(counter_html + btn_html + empty_html + toast_html, 200)
    return "", 200


@app.route("/watchlist")
@login_required
def watchlist():
    user_id = session["user_id"]
    watches = WatchedClass.query.filter_by(user_id=user_id).order_by(WatchedClass.created_at.desc()).all()

    # Get watcher counts for all tracked classes
    from sqlalchemy import func as sa_func
    count_query = (
        db.session.query(
            WatchedClass.subject, WatchedClass.catalog_number, WatchedClass.section,
            sa_func.count(WatchedClass.id).label("cnt"),
        )
        .filter(WatchedClass.term.in_([w.term for w in watches]))
        .group_by(WatchedClass.subject, WatchedClass.catalog_number, WatchedClass.section)
        .all()
    ) if watches else []
    watcher_counts = {(s, c, sec): cnt for s, c, sec, cnt in count_query}

    watch_data = []
    for w in watches:
        status = ClassStatus.query.filter_by(
            subject=w.subject, catalog_number=w.catalog_number,
            section=w.section, term=w.term
        ).first()
        wc = watcher_counts.get((w.subject, w.catalog_number, w.section), 0)
        watch_data.append({"watch": w, "status": status, "watcher_count": wc})

    return render_template("partials/watchlist_list.html", watch_data=watch_data)


@app.route("/health")
def health():
    consecutive_failures = _scheduler_state["consecutive_failures"]
    status = "ok" if consecutive_failures < MAX_CONSECUTIVE_FAILURES else "degraded"
    return {
        "status": status,
        "scheduler_running": scheduler.running,
        "last_successful_check": _scheduler_state["last_successful_check"],
        "consecutive_failures": consecutive_failures,
        "total_users": User.query.count(),
        "total_watched_classes": WatchedClass.query.count(),
    }


@app.route("/cron/check", methods=["GET", "POST"])
def cron_check():
    """External cron endpoint to trigger a class check.

    This allows free external cron services (like cron-job.org) to wake
    the service AND trigger a check, ensuring notifications work even if
    Railway sleeps the service.
    """
    secret = request.args.get("key", "")
    expected = os.environ.get("CRON_SECRET", "")
    if not expected or secret != expected:
        return {"error": "unauthorized"}, 401

    # If scheduler is running, it handles checks. Just confirm alive.
    if scheduler.running:
        return {"status": "alive", "scheduler": "running"}

    # Scheduler not running — restart it
    try:
        start_services()
        return {"status": "restarted", "scheduler": "restarted"}
    except Exception as e:
        logger.error(f"Failed to restart services from cron: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route("/admin/stats")
@login_required
def admin_stats():
    """Simple admin stats page — only accessible to the first registered user (admin)."""
    user = db.session.get(User, session["user_id"])
    if user.id != 1:
        return redirect(url_for("dashboard"))

    from sqlalchemy import func

    total_users = User.query.count()
    total_watches = WatchedClass.query.count()
    total_notifications = Notification.query.count()
    distinct_classes = db.session.query(
        WatchedClass.subject, WatchedClass.catalog_number, WatchedClass.section
    ).distinct().count()

    recent_users = User.query.order_by(User.created_at.desc()).limit(20).all()
    recent_notifications = (
        db.session.query(Notification, User)
        .join(User, Notification.user_id == User.id)
        .order_by(Notification.sent_at.desc())
        .limit(20)
        .all()
    )

    # Per-user watch counts
    user_watches = (
        db.session.query(User.name, User.email, func.count(WatchedClass.id).label("count"))
        .join(WatchedClass, User.id == WatchedClass.user_id)
        .group_by(User.id)
        .order_by(func.count(WatchedClass.id).desc())
        .all()
    )

    return render_template(
        "admin_stats.html",
        total_users=total_users,
        total_watches=total_watches,
        total_notifications=total_notifications,
        distinct_classes=distinct_classes,
        recent_users=recent_users,
        recent_notifications=recent_notifications,
        user_watches=user_watches,
    )


@app.errorhandler(429)
def ratelimit_handler(e):
    return '<div class="p-3 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">Too many requests. Please slow down.</div>', 429


# --- Admin alerting ---

def send_admin_alert(subject, body):
    """Email the admin (user.id == 1) on critical errors. Rate-limited to 1/hour."""
    now = datetime.now(timezone.utc)
    last_alert = _scheduler_state.get("last_alert_time")
    if last_alert and (now - last_alert).total_seconds() < ALERT_COOLDOWN_SECONDS:
        logger.warning("Admin alert suppressed (rate limit): %s", subject)
        return False

    try:
        with app.app_context():
            admin = db.session.get(User, 1)
            if not admin or not admin.email:
                logger.warning("No admin user (id=1) or admin has no email; cannot send alert")
                return False

            settings = _email_settings(app.config)
            if not settings["from_email"]:
                logger.warning("No notification sender configured; cannot send admin alert")
                return False

            provider = settings["provider"]
            sent = False
            if provider == "resend":
                sent = _send_via_resend(settings, admin.email, subject, body)
            elif provider == "smtp":
                sent = _send_via_smtp(settings, admin.email, subject, body)
            elif provider == "gmail_api":
                gmail_settings = dict(settings["gmail"])
                gmail_settings["sender"] = settings["from_email"]
                gmail_settings["reply_to"] = settings["reply_to"]
                sent = _send_via_gmail(gmail_settings, admin.email, subject, body)

            if sent:
                _scheduler_state["last_alert_time"] = now
                logger.info("Admin alert sent: %s", subject)
            return sent
    except Exception as exc:
        logger.error("Failed to send admin alert: %s", exc)
        return False


# --- Background job ---

def check_watched_classes():
    """Background job: check all watched classes for availability changes.

    Scrapes each unique (term, subject, catalog_number) once regardless of how
    many users watch it. On a CLOSED -> OPEN transition, all watchers of that
    section are notified individually.
    """
    with app.app_context():
        try:
            watched = db.session.query(
                WatchedClass.term, WatchedClass.subject, WatchedClass.catalog_number
            ).distinct().all()

            if not watched:
                return

            logger.info("Background job started", extra={"event": "bg_job_start", "distinct_classes": len(watched)})

            class_list = [(term, subj, cat) for term, subj, cat in watched]
            try:
                all_results = scraper.check_classes(class_list)
            except Exception as exc:
                _scheduler_state["consecutive_failures"] += 1
                count = _scheduler_state["consecutive_failures"]
                logger.error("Scraper failed", extra={"event": "scraper_error", "consecutive_failures": count, "error": str(exc)})
                if count >= MAX_CONSECUTIVE_FAILURES:
                    logger.critical(f"Scraper has failed {count} times in a row!")
                    send_admin_alert(
                        f"[Add/Drop] Scraper failing — {count} consecutive errors",
                        f"The background scraper has failed {count} times in a row.\n\n"
                        f"Latest error: {exc}\n\n"
                        f"The scheduler is still running but class checks are not completing. "
                        f"Please investigate.",
                    )
                return

            now = datetime.now(timezone.utc)
            notified_count = 0

            for (subject, catalog_number, term), results in all_results.items():
                for r in results:
                    try:
                        cs = ClassStatus.query.filter_by(
                            subject=subject, catalog_number=catalog_number,
                            section=r["section"], term=term
                        ).first()

                        old_status = cs.status if cs else None

                        if cs:
                            cs.course_name = r["course_name"]
                            cs.enrolled = r["enrolled"]
                            cs.capacity = r["capacity"]
                            cs.instructor = r.get("instructor", "")
                            cs.schedule = r.get("schedule", "")
                            cs.class_nbr = r.get("class_nbr", "")
                            if cs.status != r["status"]:
                                cs.last_changed = now
                            cs.status = r["status"]
                            cs.last_checked = now
                        else:
                            cs = ClassStatus(
                                subject=subject, catalog_number=catalog_number,
                                section=r["section"], term=term,
                                course_name=r["course_name"], enrolled=r["enrolled"],
                                capacity=r["capacity"], status=r["status"],
                                instructor=r.get("instructor", ""),
                                schedule=r.get("schedule", ""),
                                class_nbr=r.get("class_nbr", ""),
                                last_checked=now, last_changed=now,
                            )
                            db.session.add(cs)
                            db.session.flush()

                        # Notify on CLOSED → OPEN transition
                        if old_status and old_status == "Closed" and r["status"] == "Open":
                            watchers = WatchedClass.query.filter_by(
                                subject=subject, catalog_number=catalog_number,
                                section=r["section"], term=term
                            ).all()
                            for w in watchers:
                                try:
                                    user = db.session.get(User, w.user_id)
                                    if not user or not user.email:
                                        continue
                                    # Build app URL for untrack link in email
                                    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
                                    app_url = f"https://{domain}" if domain else ""
                                    success = notify_user(
                                        app.config,
                                        user.email,
                                        subject, catalog_number, r["section"],
                                        r["course_name"], r["enrolled"], r["capacity"],
                                        app_url=app_url,
                                    )
                                    if success:
                                        notif = Notification(
                                            user_id=user.id, class_status_id=cs.id,
                                            message=f"{subject} {catalog_number} Sec {r['section']} is now Open ({r['enrolled']}/{r['capacity']})",
                                        )
                                        db.session.add(notif)
                                        notified_count += 1
                                        logger.info("Notification sent", extra={"event": "notification_sent", "user_id": user.id, "class": f"{subject} {catalog_number} Sec {r['section']}"})
                                except Exception as exc:
                                    logger.error(f"Failed to notify user {w.user_id} for {subject} {catalog_number}: {exc}")

                        db.session.commit()
                    except Exception as exc:
                        logger.error(f"Error processing {subject} {catalog_number} Sec {r.get('section', '?')}: {exc}")
                        db.session.rollback()
                        continue  # Continue to next class — don't abort the batch

            # Scraper succeeded: reset failure counter, record success time
            _scheduler_state["consecutive_failures"] = 0
            _scheduler_state["last_successful_check"] = now.isoformat()
            logger.info("Background job complete", extra={"event": "bg_job_complete", "notified_count": notified_count})
        except Exception as exc:
            _scheduler_state["consecutive_failures"] += 1
            count = _scheduler_state["consecutive_failures"]
            logger.error("Background job failed", extra={"event": "bg_job_fail", "consecutive_failures": count, "error": str(exc)})
            db.session.rollback()
            if count >= MAX_CONSECUTIVE_FAILURES:
                logger.critical(f"Background job has failed {count} times in a row!")
                send_admin_alert(
                    f"[Add/Drop] Background job failing — {count} consecutive errors",
                    f"The background check job has failed {count} times in a row.\n\n"
                    f"Latest error: {exc}\n\n"
                    f"This may indicate a database or scraper issue. Please investigate.",
                )


# --- App lifecycle ---

def start_services():
    """Start scraper and scheduler."""
    try:
        scraper.start()
    except Exception as e:
        logger.error(f"Failed to start scraper: {e}")

    scheduler.add_job(
        check_watched_classes, "interval",
        seconds=app.config["CHECK_INTERVAL_SECONDS"],
        max_instances=1, misfire_grace_time=30,
        id="check_classes",
    )

    # Self-ping to prevent Railway from sleeping the service
    def keep_alive():
        """Ping our own health endpoint to prevent idle sleep."""
        import urllib.request
        try:
            url = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
            if url:
                urllib.request.urlopen(f"https://{url}/health", timeout=10)
                logger.debug("Keep-alive ping sent")
        except Exception:
            pass  # Non-critical, just preventing sleep

    scheduler.add_job(
        keep_alive, "interval",
        minutes=5,
        id="keep_alive",
    )

    scheduler.start()
    logger.info(f"Scheduler started: checking every {app.config['CHECK_INTERVAL_SECONDS']}s")


def stop_services():
    """Shutdown scraper and scheduler."""
    scheduler.shutdown(wait=False)
    scraper.stop()


_using_sqlite = app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")

with app.app_context():
    db.create_all()

    if _using_sqlite:
        # SQLite: enable WAL mode and busy timeout for concurrent access
        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA journal_mode=WAL"))
            conn.execute(db.text("PRAGMA busy_timeout=5000"))
            conn.commit()
        logger.info("SQLite: WAL mode enabled, busy_timeout=5000ms")
    else:
        logger.info("Using PostgreSQL database")

    # Add indexes for hot query paths (works on both SQLite and Postgres)
    with db.engine.connect() as conn:
        conn.execute(db.text(
            "CREATE INDEX IF NOT EXISTS ix_class_status_lookup "
            "ON class_status (subject, catalog_number, section, term)"
        ))
        conn.execute(db.text(
            "CREATE INDEX IF NOT EXISTS ix_watched_user "
            "ON watched_classes (user_id, term)"
        ))
        conn.execute(db.text(
            "CREATE INDEX IF NOT EXISTS ix_watched_class_lookup "
            "ON watched_classes (subject, catalog_number, section, term)"
        ))
        conn.commit()

    # Migrate existing DB: add new columns if missing
    if _using_sqlite:
        with db.engine.connect() as conn:
            columns = [row[1] for row in conn.execute(db.text("PRAGMA table_info(users)"))]
            if "email" not in columns:
                conn.execute(db.text("ALTER TABLE users ADD COLUMN email VARCHAR(200)"))
                conn.commit()
                logger.info("Migrated: added email column to users")
            if "ntfy_topic" not in columns:
                conn.execute(db.text("ALTER TABLE users ADD COLUMN ntfy_topic VARCHAR(120)"))
                conn.commit()
                logger.info("Migrated: added ntfy_topic column to users")
            if "google_id" not in columns:
                conn.execute(db.text("ALTER TABLE users ADD COLUMN google_id VARCHAR(200)"))
                conn.commit()
                logger.info("Migrated: added google_id column to users")
            if "name" not in columns:
                conn.execute(db.text("ALTER TABLE users ADD COLUMN name VARCHAR(200)"))
                conn.commit()
                logger.info("Migrated: added name column to users")
            conn.execute(
                db.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_ntfy_topic ON users (ntfy_topic)")
            )
            conn.commit()
    else:
        # Postgres: add columns if they don't exist (idempotent)
        with db.engine.connect() as conn:
            for col, coltype in [("email", "VARCHAR(200)"), ("ntfy_topic", "VARCHAR(120)"),
                                  ("google_id", "VARCHAR(200)"), ("name", "VARCHAR(200)")]:
                conn.execute(db.text(
                    f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {coltype}"
                ))
            conn.execute(db.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_ntfy_topic ON users (ntfy_topic)"
            ))
            conn.commit()

    users_missing_topic = User.query.filter(
        (User.ntfy_topic.is_(None)) | (User.ntfy_topic == "")
    ).all()
    for user in users_missing_topic:
        user.ntfy_topic = build_unique_ntfy_topic(user.email, user.name or user.username)
    if users_missing_topic:
        db.session.commit()
        logger.info("Migrated: populated ntfy_topic for %s users", len(users_missing_topic))

if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    start_services()
    atexit.register(stop_services)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, port=port)
