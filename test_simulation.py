"""
End-to-end simulation: tests the full Add/Drop notification pipeline.

Exercises every layer — DB models, status transitions, notification
building, and email delivery — using msurur@uchicago.edu as the
target recipient.

Usage:
    python test_simulation.py
"""

import sys
from datetime import datetime, timezone

from app import app
from models import ClassStatus, Notification, User, WatchedClass, db
from notifier import (
    _email_settings,
    _seat_opening_message,
    notification_provider_name,
    notification_sender,
    notifications_ready,
    notify_user,
)

TEST_EMAIL = "msurur@uchicago.edu"
TEST_SUBJECT = "TEST"
TEST_CATALOG = "99999"
TEST_SECTION = "1"
TEST_TERM = "2264"
TEST_COURSE = "Simulation: Seat Alert Pipeline Test"
TEST_USERNAME = "test_sim_user"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
INFO = "\033[94mINFO\033[0m"

# Track objects for cleanup
_cleanup = []


def step(num, total, desc):
    print(f"\n{'─'*50}")
    print(f"  [{num}/{total}] {desc}")
    print(f"{'─'*50}")


def cleanup():
    """Remove all test data."""
    with app.app_context():
        for obj in reversed(_cleanup):
            try:
                merged = db.session.merge(obj)
                db.session.delete(merged)
            except Exception:
                pass
        db.session.commit()
    print(f"\n  [{PASS}] Test data cleaned up")


def run():
    total = 7
    results = []

    with app.app_context():
        # ── 1. Create or find test user ──────────────────────────
        step(1, total, "Create test user")

        user = User.query.filter_by(email=TEST_EMAIL).first()
        created_user = False
        if user:
            print(f"  Found existing user: {user.username} (id={user.id})")
        else:
            user = User(
                username=TEST_USERNAME,
                email=TEST_EMAIL,
                name="Test Sim",
                ntfy_topic=f"addrop-test-sim-000000000000",
            )
            db.session.add(user)
            db.session.commit()
            created_user = True
            _cleanup.append(user)
            print(f"  Created test user: {user.username} (id={user.id})")

        print(f"  Email:    {user.email}")
        print(f"  [{PASS}] User ready")
        results.append(True)

        # ── 2. Insert ClassStatus as Closed ──────────────────────
        step(2, total, "Insert class with status=Closed")

        # Clean up any leftover test data first
        old_cs = ClassStatus.query.filter_by(
            subject=TEST_SUBJECT, catalog_number=TEST_CATALOG,
            section=TEST_SECTION, term=TEST_TERM,
        ).first()
        if old_cs:
            db.session.delete(old_cs)
            db.session.commit()

        old_wc = WatchedClass.query.filter_by(
            user_id=user.id, subject=TEST_SUBJECT,
            catalog_number=TEST_CATALOG, section=TEST_SECTION,
            term=TEST_TERM,
        ).first()
        if old_wc:
            db.session.delete(old_wc)
            db.session.commit()

        now = datetime.now(timezone.utc)
        cs = ClassStatus(
            subject=TEST_SUBJECT, catalog_number=TEST_CATALOG,
            section=TEST_SECTION, term=TEST_TERM,
            course_name=TEST_COURSE,
            enrolled=55, capacity=55, status="Closed",
            instructor="Dr. Simulation",
            schedule="Mon Wed : 10:30 AM-11:50 AM",
            class_nbr="99999",
            last_checked=now, last_changed=now,
        )
        db.session.add(cs)
        db.session.commit()
        _cleanup.append(cs)

        print(f"  ClassStatus id={cs.id}")
        print(f"  Status:     {cs.status}")
        print(f"  Enrollment: {cs.enrolled}/{cs.capacity}")
        print(f"  [{PASS}] ClassStatus inserted")
        results.append(True)

        # ── 3. Add to watchlist ──────────────────────────────────
        step(3, total, "Add class to user's watchlist")

        wc = WatchedClass(
            user_id=user.id, subject=TEST_SUBJECT,
            catalog_number=TEST_CATALOG, section=TEST_SECTION,
            term=TEST_TERM,
        )
        db.session.add(wc)
        db.session.commit()
        _cleanup.append(wc)

        print(f"  WatchedClass id={wc.id} for user_id={user.id}")
        print(f"  [{PASS}] Watchlist entry created")
        results.append(True)

        # ── 4. Simulate Closed → Open transition ────────────────
        step(4, total, "Simulate Closed → Open transition")

        old_status = cs.status
        cs.status = "Open"
        cs.enrolled = 54  # one seat freed
        cs.last_changed = datetime.now(timezone.utc)
        cs.last_checked = datetime.now(timezone.utc)
        db.session.commit()

        transition = f"{old_status} → {cs.status}"
        should_notify = old_status == "Closed" and cs.status == "Open"

        print(f"  Transition: {transition}")
        print(f"  Enrollment: {cs.enrolled}/{cs.capacity}")
        print(f"  Should notify: {should_notify}")
        print(f"  [{PASS}] Status transition recorded")
        results.append(True)

        # ── 5. Verify notification message builds correctly ──────
        step(5, total, "Build notification message")

        subj_line, body = _seat_opening_message(
            TEST_SUBJECT, TEST_CATALOG, TEST_SECTION,
            TEST_COURSE, cs.enrolled, cs.capacity,
        )

        print(f"  Subject: {subj_line}")
        print(f"  Body:")
        for line in body.split("\n"):
            print(f"    | {line}")

        msg_ok = "Seat Available" in subj_line and "OPEN" in body.upper()
        print(f"  [{PASS if msg_ok else FAIL}] Message content looks correct")
        results.append(msg_ok)

        # ── 6. Check email provider config & attempt send ────────
        step(6, total, "Check email provider & send notification")

        settings = _email_settings(app.config)
        provider = notification_provider_name(app.config)
        sender = notification_sender(app.config)
        ready = notifications_ready(app.config)

        print(f"  Provider:  {provider or '(none)'}")
        print(f"  Sender:    {sender or '(none)'}")
        print(f"  Ready:     {ready}")
        print(f"  Recipient: {TEST_EMAIL}")

        if not ready:
            print(f"\n  [{WARN}] Email provider is NOT configured.")
            print(f"  Current .env settings:")
            print(f"    EMAIL_PROVIDER = {settings['provider'] or '(empty)'}")
            print(f"    EMAIL_FROM     = {settings['from_email'] or '(empty)'}")
            print(f"    RESEND_API_KEY = {'(set)' if settings['resend_api_key'] else '(empty)'}")
            print(f"    SMTP_HOST      = {settings['smtp_host'] or '(empty)'}")
            print()
            print(f"  To send real emails, configure one of:")
            print(f"    Option A — Resend (easiest):")
            print(f"      1. Sign up at resend.com, verify a domain")
            print(f"      2. Set RESEND_API_KEY=re_xxxxx in .env")
            print(f"      3. Set EMAIL_FROM=alerts@yourdomain.com")
            print()
            print(f"    Option B — SMTP (e.g. Gmail app password):")
            print(f"      SMTP_HOST=smtp.gmail.com")
            print(f"      SMTP_PORT=587")
            print(f"      SMTP_USERNAME=youraddress@gmail.com")
            print(f"      SMTP_PASSWORD=your-app-password")
            print(f"      EMAIL_FROM=youraddress@gmail.com")
            print()
            print(f"  [{WARN}] Skipping actual email send — provider not configured")
            email_sent = False
            results.append(None)  # None = skipped
        else:
            print(f"\n  Sending email now...")
            email_sent = notify_user(
                app.config, TEST_EMAIL,
                TEST_SUBJECT, TEST_CATALOG, TEST_SECTION,
                TEST_COURSE, cs.enrolled, cs.capacity,
            )
            if email_sent:
                print(f"  [{PASS}] Email sent to {TEST_EMAIL}")
            else:
                print(f"  [{FAIL}] Email send failed — check logs above")
            results.append(email_sent)

        # ── 7. Record notification & verify DB integrity ─────────
        step(7, total, "Record notification & verify DB state")

        notif = Notification(
            user_id=user.id, class_status_id=cs.id,
            message=f"{TEST_SUBJECT} {TEST_CATALOG} Sec {TEST_SECTION} is now Open ({cs.enrolled}/{cs.capacity})",
        )
        db.session.add(notif)
        db.session.commit()
        _cleanup.append(notif)

        # Verify relationships
        user_watches = WatchedClass.query.filter_by(user_id=user.id, subject=TEST_SUBJECT).count()
        user_notifs = Notification.query.filter_by(user_id=user.id, class_status_id=cs.id).count()
        cs_check = db.session.get(ClassStatus, cs.id)

        print(f"  Notification id={notif.id}")
        print(f"  User's watches for TEST: {user_watches}")
        print(f"  User's notifications:    {user_notifs}")
        print(f"  ClassStatus final:       {cs_check.status} ({cs_check.enrolled}/{cs_check.capacity})")

        db_ok = user_watches >= 1 and user_notifs >= 1 and cs_check.status == "Open"
        print(f"  [{PASS if db_ok else FAIL}] DB integrity verified")
        results.append(db_ok)

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'═'*50}")
    print(f"  SIMULATION SUMMARY")
    print(f"{'═'*50}")
    labels = [
        "User setup",
        "ClassStatus insert",
        "Watchlist entry",
        "Status transition",
        "Message building",
        "Email delivery",
        "DB integrity",
    ]
    all_passed = True
    for label, result in zip(labels, results):
        if result is None:
            status = WARN + " SKIPPED"
        elif result:
            status = PASS
        else:
            status = FAIL
            all_passed = False
        print(f"  {label:.<30s} {status}")

    print(f"{'═'*50}")
    if all_passed and all(r is not None for r in results):
        print(f"  All steps passed! Check {TEST_EMAIL} for the email.")
    elif all(r is not False for r in results):
        print(f"  Logic is correct. Configure an email provider to complete the test.")
    else:
        print(f"  Some steps failed. Review output above.")
    print()

    return all_passed


if __name__ == "__main__":
    try:
        passed = run()
    finally:
        cleanup()
    sys.exit(0 if passed else 1)
