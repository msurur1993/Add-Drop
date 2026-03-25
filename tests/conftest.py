import os
import sys
import pytest

# Ensure the project root is on sys.path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functools import wraps

from flask import Flask, make_response, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from models import db, User, WatchedClass, ClassStatus, Notification
from scraper import PeopleSoftScraper

MAX_WATCHES_PER_USER = 5


def _register_routes(test_app):
    """Register the /watch and /unwatch routes on the test app.

    These mirror the production routes in app.py but without rate-limiting
    or the scraper/scheduler side-effects that come from importing app.py.
    """

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect("/")
            user = db.session.get(User, session["user_id"])
            if not user:
                session.clear()
                return redirect("/")
            return f(*args, **kwargs)
        return decorated

    @test_app.route("/watch", methods=["POST"])
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
                f'{subject} {catalog_number} is open \u2014 go enroll now!</div></div>'
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
            wc = WatchedClass(
                user_id=user_id, subject=subject,
                catalog_number=catalog_number, section=section, term=term,
            )
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

        from sqlalchemy import func as sa_func
        watcher_count = WatchedClass.query.filter_by(
            subject=subject, catalog_number=catalog_number, section=section, term=term
        ).count()

        btn_id = f"track-btn-{subject}-{catalog_number}-{section}"
        watchlist_html = render_template(
            "partials/watchlist_item.html", watch=w, status=status, watcher_count=watcher_count,
        )
        oob_html = (
            f'<span id="{btn_id}" hx-swap-oob="true" '
            f'class="text-xs text-gray-400 px-3 py-1.5 bg-gray-100 rounded-lg">Tracking</span>'
        )
        counter_html = (
            f'<span id="slot-counter" hx-swap-oob="true" '
            f'class="text-xs text-gray-400">{new_count}/5 slots used</span>'
        )
        empty_html = '<p id="empty-watchlist" hx-swap-oob="true"></p>'
        toast_html = (
            '<div hx-swap-oob="afterbegin:#toast-area">'
            f'<div class="toast bg-green-50 text-green-700 border border-green-200">'
            f'Now tracking {subject} {catalog_number} Sec {section}</div></div>'
        )
        resp = make_response(watchlist_html + oob_html + counter_html + empty_html + toast_html)
        return resp

    @test_app.route("/unwatch/<int:watch_id>", methods=["DELETE"])
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
            new_count = WatchedClass.query.filter_by(user_id=session["user_id"]).count()

            counter_html = (
                f'<span id="slot-counter" hx-swap-oob="true" '
                f'class="text-xs text-gray-400">{new_count}/5 slots used</span>'
            )
            btn_id = f"track-btn-{subject}-{catalog_number}-{section}"
            btn_html = (
                f'<button id="{btn_id}" hx-swap-oob="true"'
                f' hx-post="/watch"'
                f""" hx-vals='{{"subject": "{subject}", "catalog_number": "{catalog_number}", "section": "{section}", "term": "{term}"}}'"""
                f' hx-target="#watchlist" hx-swap="afterbegin"'
                f' class="text-xs px-3 py-1.5 bg-[#800000] hover:bg-[#9A2A2A] text-white rounded-lg transition">'
                f'Track</button>'
            )
            empty_html = ""
            if new_count == 0:
                empty_html = (
                    '<p id="empty-watchlist" hx-swap-oob="true" '
                    'class="text-gray-400 text-sm">No classes tracked yet. '
                    'Search and add classes to start monitoring.</p>'
                )
            toast_html = (
                '<div hx-swap-oob="afterbegin:#toast-area">'
                f'<div class="toast bg-gray-50 text-gray-700 border border-gray-200">'
                f'Removed {label} from watchlist</div></div>'
            )
            return make_response(counter_html + btn_html + empty_html + toast_html, 200)
        return "", 200


@pytest.fixture()
def scraper():
    """A PeopleSoftScraper instance (only used for its parser, no browser)."""
    return PeopleSoftScraper({"PEOPLESOFT_URL": "http://test", "PLAYWRIGHT_HEADLESS": True})


@pytest.fixture()
def app(tmp_path):
    """Create a minimal Flask app wired to an in-memory SQLite database."""
    test_app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    )
    test_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        CURRENT_TERM="2264",
        PEOPLESOFT_URL="http://test",
        PLAYWRIGHT_HEADLESS=True,
        GOOGLE_CLIENT_ID="",
        GOOGLE_CLIENT_SECRET="",
        # Resend email config for notification tests
        EMAIL_PROVIDER="resend",
        EMAIL_FROM="alerts@example.com",
        RESEND_API_KEY="re_test_key_123",
        EMAIL_REPLY_TO="",
        # Gmail keys (empty -- not used in tests)
        GMAIL_SENDER="",
        GMAIL_CLIENT_ID="",
        GMAIL_CLIENT_SECRET="",
        GMAIL_REFRESH_TOKEN="",
        GMAIL_TOKEN_URI="",
        GMAIL_CREDENTIALS_FILE="",
        GMAIL_TOKEN_FILE="",
        GMAIL_ENABLE_INTERACTIVE_AUTH="false",
        SMTP_HOST="",
        SMTP_PORT=587,
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_USE_TLS="true",
        SMTP_USE_SSL="false",
        CHECK_INTERVAL_SECONDS=300,
    )

    # Register the chicago_time template filter used by watchlist_item.html
    from datetime import timezone
    from zoneinfo import ZoneInfo

    CHICAGO_TZ = ZoneInfo("America/Chicago")

    @test_app.template_filter("chicago_time")
    def chicago_time_filter(dt):
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(CHICAGO_TZ).strftime("%-I:%M %p")

    db.init_app(test_app)
    _register_routes(test_app)

    with test_app.app_context():
        db.create_all()

    yield test_app


@pytest.fixture()
def client(app):
    """Flask test client with a logged-in user already in the session."""
    with app.app_context():
        user = User(
            username="testuser",
            ntfy_topic="addrop-testuser-abc123",
            email="test@uchicago.edu",
            google_id="google-test-123",
            name="Test User",
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = "Test User"
        yield c


@pytest.fixture()
def seed_user(app):
    """Return a helper that creates and returns a User inside the app context."""
    def _create(username="watcher", email="watcher@uchicago.edu"):
        with app.app_context():
            u = User(
                username=username,
                ntfy_topic=f"addrop-{username}-aaa111",
                email=email,
                google_id=f"gid-{username}",
                name=username.title(),
            )
            db.session.add(u)
            db.session.commit()
            return u.id
    return _create
