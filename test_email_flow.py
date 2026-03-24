"""
Integration test: Closed -> Open email notification flow.

Inserts a fake class, flips it from Closed to Open, sends a real email
through the configured provider, then cleans up test data.

Prerequisites:
    1. Configure one of:
       - EMAIL_PROVIDER=resend with EMAIL_FROM and RESEND_API_KEY
       - EMAIL_PROVIDER=smtp with EMAIL_FROM and SMTP_* settings
       - EMAIL_PROVIDER=gmail_api with the legacy GMAIL_* settings
    2. User "muaz" must have an email set in the dashboard

Usage:
    python test_email_flow.py
"""

import sys
from datetime import datetime, timezone

from app import app
from models import ClassStatus, Notification, User, WatchedClass, db
from notifier import notification_provider_name, notification_sender, notify_user

TEST_SUBJECT = "TEST"
TEST_CATALOG = "99999"
TEST_SECTION = "1"
TEST_TERM = "2264"
TEST_COURSE_NAME = "Integration Test: Email Notification"
USERNAME = "muaz"


def run_test():
    with app.app_context():
        # --- Step 1: Find user ---
        user = User.query.filter_by(username=USERNAME).first()
        if not user:
            print(f"FAIL: User '{USERNAME}' not found in DB")
            return False

        if not user.email:
            print(f"FAIL: User '{USERNAME}' has no email set. Add one via the dashboard first.")
            return False

        print(f"[1/7] Found user '{user.username}' with email: {user.email}")

        # --- Step 2: Insert fake Closed class + watch ---
        cs = ClassStatus(
            subject=TEST_SUBJECT, catalog_number=TEST_CATALOG,
            section=TEST_SECTION, term=TEST_TERM,
            course_name=TEST_COURSE_NAME,
            enrolled=55, capacity=55, status="Closed",
            instructor="Test Instructor",
            schedule="Mon Wed : 10:30 AM-11:50 AM",
            last_checked=datetime.now(timezone.utc),
            last_changed=datetime.now(timezone.utc),
        )
        db.session.add(cs)
        db.session.flush()

        wc = WatchedClass(
            user_id=user.id, subject=TEST_SUBJECT,
            catalog_number=TEST_CATALOG, section=TEST_SECTION,
            term=TEST_TERM,
        )
        db.session.add(wc)
        db.session.commit()
        print(f"[2/7] Inserted ClassStatus (Closed) and WatchedClass for {TEST_SUBJECT} {TEST_CATALOG}")

        # --- Step 3: Flip to Open ---
        cs.status = "Open"
        cs.enrolled = 54
        cs.last_changed = datetime.now(timezone.utc)
        db.session.commit()
        print(f"[3/7] Flipped status: Closed -> Open")

        # --- Step 4: Send real email ---
        sender = notification_sender(app.config) or "(unset sender)"
        provider = notification_provider_name(app.config) or "unknown provider"
        print(f"[4/7] Sending email to {user.email} from {sender} via {provider}...")

        success = notify_user(
            app.config,
            user.email,
            TEST_SUBJECT, TEST_CATALOG, TEST_SECTION,
            TEST_COURSE_NAME, 54, 55,
        )

        # --- Step 5: Record notification ---
        notif = None
        if success:
            notif = Notification(
                user_id=user.id, class_status_id=cs.id,
                message=f"{TEST_SUBJECT} {TEST_CATALOG} Sec {TEST_SECTION} is now Open (54/55)",
            )
            db.session.add(notif)
            db.session.commit()
            print(f"[5/7] Email sent successfully! Notification record created.")
        else:
            print(f"[5/7] FAIL: Email send failed. Check logs above.")

        # --- Step 6: Print results ---
        print(f"[6/7] Result: {'PASS' if success else 'FAIL'}")
        if success:
            print(f"       Check {user.email} for email with subject 'Seat Available: TEST 99999'")

        # --- Step 7: Cleanup ---
        cleanup(cs, wc, notif)
        print(f"[7/7] Test data cleaned up")

        return success


def cleanup(cs, wc, notif):
    with app.app_context():
        if notif and notif.id:
            db.session.execute(db.delete(Notification).where(Notification.id == notif.id))
        if wc and wc.id:
            db.session.execute(db.delete(WatchedClass).where(WatchedClass.id == wc.id))
        if cs and cs.id:
            db.session.execute(db.delete(ClassStatus).where(ClassStatus.id == cs.id))
        db.session.commit()


if __name__ == "__main__":
    passed = run_test()
    sys.exit(0 if passed else 1)
