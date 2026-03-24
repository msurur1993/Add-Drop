import atexit
import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from functools import wraps
from zoneinfo import ZoneInfo

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
    notification_provider_name,
    notification_sender,
    notifications_ready,
    notify_user,
)
from scraper import PeopleSoftScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MAX_WATCHES_PER_USER = 5

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
            return redirect(url_for("index"))
        user = db.session.get(User, session["user_id"])
        if not user:
            session.clear()
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

    session["user_id"] = user.id
    session["username"] = user.name or user.username
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

    watch_data = []
    for w in watches:
        status = ClassStatus.query.filter_by(
            subject=w.subject, catalog_number=w.catalog_number,
            section=w.section, term=w.term
        ).first()
        watch_data.append({"watch": w, "status": status})

    return render_template(
        "dashboard.html",
        user=user,
        watch_data=watch_data,
        watch_count=len(watches),
        term=app.config["CURRENT_TERM"],
        departments=DEPARTMENTS,
        notifications_ready=notifications_ready(app.config),
        notification_provider=notification_provider_name(app.config),
        notification_sender=notification_sender(app.config),
    )


@app.route("/search", methods=["POST"])
@limiter.limit("10/minute")
@login_required
def search():
    subject = request.form.get("subject", "").strip().upper()
    keyword = request.form.get("keyword", "").strip()
    term = app.config["CURRENT_TERM"]

    if not keyword:
        return render_template("partials/search_results.html", results=[], error="Enter a course name, number, or instructor.")

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

    return render_template(
        "partials/search_results.html",
        results=results, term=term, watched_keys=watched_keys, error=None,
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
        db.session.commit()

    status = ClassStatus.query.filter_by(
        subject=subject, catalog_number=catalog_number, section=section, term=term
    ).first()

    w = existing or wc
    new_count = WatchedClass.query.filter_by(user_id=user_id).count()

    btn_id = f"track-btn-{subject}-{catalog_number}-{section}"
    watchlist_html = render_template("partials/watchlist_item.html", watch=w, status=status)
    oob_html = f'<span id="{btn_id}" hx-swap-oob="true" class="text-xs text-gray-400 px-3 py-1.5 bg-gray-100 rounded-lg">Tracking</span>'
    counter_html = f'<span id="slot-counter" hx-swap-oob="true" class="text-xs text-gray-400">{new_count}/5 slots used</span>'
    toast_html = (
        '<div hx-swap-oob="afterbegin:#toast-area">'
        f'<div class="toast bg-green-50 text-green-700 border border-green-200">'
        f'Now tracking {subject} {catalog_number} Sec {section}</div></div>'
    )

    resp = make_response(watchlist_html + oob_html + counter_html + toast_html)
    return resp


@app.route("/unwatch/<int:watch_id>", methods=["DELETE"])
@login_required
def unwatch(watch_id):
    wc = WatchedClass.query.filter_by(id=watch_id, user_id=session["user_id"]).first()
    if wc:
        label = f"{wc.subject} {wc.catalog_number} Sec {wc.section}"
        db.session.delete(wc)
        db.session.commit()
        new_count = WatchedClass.query.filter_by(user_id=session["user_id"]).count()
        counter_html = f'<span id="slot-counter" hx-swap-oob="true" class="text-xs text-gray-400">{new_count}/5 slots used</span>'
        toast_html = (
            '<div hx-swap-oob="afterbegin:#toast-area">'
            f'<div class="toast bg-gray-50 text-gray-700 border border-gray-200">'
            f'Removed {label} from watchlist</div></div>'
        )
        return counter_html + toast_html
    return "", 200


@app.route("/watchlist")
@login_required
def watchlist():
    user_id = session["user_id"]
    watches = WatchedClass.query.filter_by(user_id=user_id).order_by(WatchedClass.created_at.desc()).all()

    watch_data = []
    for w in watches:
        status = ClassStatus.query.filter_by(
            subject=w.subject, catalog_number=w.catalog_number,
            section=w.section, term=w.term
        ).first()
        watch_data.append({"watch": w, "status": status})

    return render_template("partials/watchlist_list.html", watch_data=watch_data)


@app.route("/health")
def health():
    return {"status": "ok", "watched_count": WatchedClass.query.count()}


@app.errorhandler(429)
def ratelimit_handler(e):
    return '<div class="p-3 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">Too many requests. Please slow down.</div>', 429


# --- Background job ---

def check_watched_classes():
    """Background job: check all watched classes for availability changes.

    Scrapes each unique (term, subject, catalog_number) once regardless of how
    many users watch it. On a CLOSED -> OPEN transition, all watchers of that
    section are notified individually.
    """
    with app.app_context():
        watched = db.session.query(
            WatchedClass.term, WatchedClass.subject, WatchedClass.catalog_number
        ).distinct().all()

        if not watched:
            return

        logger.info(f"Checking {len(watched)} distinct classes...")

        class_list = [(term, subj, cat) for term, subj, cat in watched]
        all_results = scraper.check_classes(class_list)

        now = datetime.now(timezone.utc)

        for (subject, catalog_number, term), results in all_results.items():
            for r in results:
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
                        user = db.session.get(User, w.user_id)
                        success = notify_user(
                            app.config,
                            user.email,
                            subject, catalog_number, r["section"],
                            r["course_name"], r["enrolled"], r["capacity"],
                        )
                        if success:
                            notif = Notification(
                                user_id=user.id, class_status_id=cs.id,
                                message=f"{subject} {catalog_number} Sec {r['section']} is now Open ({r['enrolled']}/{r['capacity']})",
                            )
                            db.session.add(notif)

        db.session.commit()
        logger.info("Background check complete.")


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
    scheduler.start()
    logger.info(f"Scheduler started: checking every {app.config['CHECK_INTERVAL_SECONDS']}s")


def stop_services():
    """Shutdown scraper and scheduler."""
    scheduler.shutdown(wait=False)
    scraper.stop()


with app.app_context():
    db.create_all()
    # Migrate existing DB: add new columns if missing
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
