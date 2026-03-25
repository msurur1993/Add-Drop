"""
Comprehensive tests for the Add/Drop Flask application.

Covers:
  1. Scraper _parse_result_row parsing
  2. Watch / unwatch routes and slot counting
  3. Closed -> Open notification flow (background job)
  4. Email sending via Resend API (mocked)
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from models import ClassStatus, Notification, User, WatchedClass, db
from notifier import _send_via_resend, notify_user


# ---------------------------------------------------------------------------
# 1. Scraper parser tests
# ---------------------------------------------------------------------------

class TestParseResultRow:
    """Tests for PeopleSoftScraper._parse_result_row."""

    STANDARD_INPUT = (
        "The Elements of Economic Analysis II\n"
        "ECON 20100/1 [21669] - LEC In-Person Closed Consent Required\n"
        "Section Enrollment: 58/55\n"
        "Afonso\n"
        "Mon Wed : 01:30 PM-02:50 PM"
    )

    def test_standard_result(self, scraper):
        result = scraper._parse_result_row(self.STANDARD_INPUT)
        assert result is not None
        assert result["course_name"] == "The Elements of Economic Analysis II"
        assert result["subject"] == "ECON"
        assert result["catalog_number"] == "20100"
        assert result["section"] == "1"
        assert result["class_nbr"] == "21669"
        assert result["course_id"] == "ECON 20100/1"
        assert result["enrolled"] == 58
        assert result["capacity"] == 55
        assert result["status"] == "Closed"
        assert result["instructor"] == "Afonso"
        assert "Mon Wed" in result["schedule"]
        assert "01:30 PM" in result["schedule"]

    def test_open_class(self, scraper):
        text = (
            "Introduction to Computer Science I\n"
            "CMSC 15100/1 [10001] - LEC In-Person Open\n"
            "Section Enrollment: 30/50\n"
            "Instructor TBD\n"
            "Tue Thu : 09:30 AM-10:50 AM"
        )
        result = scraper._parse_result_row(text)
        assert result is not None
        assert result["status"] == "Open"
        assert result["enrolled"] == 30
        assert result["capacity"] == 50

    def test_closed_class(self, scraper):
        text = (
            "Honors Calculus III\n"
            "MATH 16300/2 [14500] - LEC In-Person Closed\n"
            "Section Enrollment: 25/25\n"
            "Neves\n"
            "Mon Wed Fri : 10:30 AM-11:20 AM"
        )
        result = scraper._parse_result_row(text)
        assert result is not None
        assert result["status"] == "Closed"
        assert result["section"] == "2"
        assert result["subject"] == "MATH"

    def test_unknown_status(self, scraper):
        text = (
            "Topics in Philosophy\n"
            "PHIL 29700/1 [18200] - LEC In-Person Consent Required\n"
            "Section Enrollment: 10/20\n"
            "Smith\n"
            "Tue Thu : 01:30 PM-02:50 PM"
        )
        result = scraper._parse_result_row(text)
        assert result is not None
        assert result["status"] == "Unknown"

    def test_missing_enrollment_data(self, scraper):
        text = (
            "Advanced Topics in Machine Learning\n"
            "CMSC 35400/1 [22000] - LEC In-Person Closed\n"
            "Risi\n"
            "Mon Wed : 03:00 PM-04:20 PM"
        )
        result = scraper._parse_result_row(text)
        assert result is not None
        assert result["enrolled"] == 0
        assert result["capacity"] == 0
        assert result["status"] == "Closed"
        assert result["class_nbr"] == "22000"

    def test_no_section_number(self, scraper):
        """Input line with no /N section number falls back to '1'."""
        text = (
            "Some Course\n"
            "HIST 12345 [99999] - LEC In-Person Open\n"
            "Section Enrollment: 5/30"
        )
        result = scraper._parse_result_row(text)
        assert result is not None
        # No /N pattern, so regex fails to match the SUBJ NNNNN/N form
        assert result["section"] == "1"  # default fallback
        assert result["status"] == "Open"

    def test_empty_string_returns_none(self, scraper):
        assert scraper._parse_result_row("") is None

    def test_single_line_returns_none(self, scraper):
        assert scraper._parse_result_row("Only one line here") is None

    def test_malformed_two_lines_still_parses(self, scraper):
        """Two lines with no recognisable format still return a dict."""
        text = "Course Title\nGarbage data no pattern"
        result = scraper._parse_result_row(text)
        assert result is not None
        assert result["course_name"] == "Course Title"
        assert result["status"] == "Unknown"
        assert result["enrolled"] == 0
        assert result["capacity"] == 0


# ---------------------------------------------------------------------------
# 2. Watch / unwatch / slot counting via Flask test client
# ---------------------------------------------------------------------------

class TestWatchUnwatch:
    """Test the /watch and /unwatch routes."""

    def _add_closed_class_status(self, app, subject="ECON", catalog="20100",
                                  section="1", term="2264"):
        """Insert a ClassStatus record with status Closed."""
        with app.app_context():
            cs = ClassStatus(
                subject=subject, catalog_number=catalog, section=section,
                term=term, course_name="Test Course", enrolled=55, capacity=55,
                status="Closed", last_checked=datetime.now(timezone.utc),
                last_changed=datetime.now(timezone.utc),
            )
            db.session.add(cs)
            db.session.commit()
            return cs.id

    def _watch_class(self, client, subject="ECON", catalog="20100",
                     section="1", term="2264"):
        return client.post("/watch", data={
            "subject": subject,
            "catalog_number": catalog,
            "section": section,
            "term": term,
        })

    def _get_slot_count(self, app, user_id):
        with app.app_context():
            return WatchedClass.query.filter_by(user_id=user_id).count()

    def test_track_class_increases_slot_count(self, app, client):
        self._add_closed_class_status(app)
        with app.app_context():
            user_id = User.query.first().id

        assert self._get_slot_count(app, user_id) == 0
        resp = self._watch_class(client)
        assert resp.status_code == 200
        assert self._get_slot_count(app, user_id) == 1
        assert b"Now tracking" in resp.data

    def test_track_five_then_sixth_rejected(self, app, client):
        """Tracking 5 classes should work; a 6th must be rejected."""
        with app.app_context():
            user_id = User.query.first().id

        for i in range(5):
            self._add_closed_class_status(
                app, subject="DEPT", catalog=str(10000 + i), section="1"
            )
            resp = self._watch_class(
                client, subject="DEPT", catalog=str(10000 + i), section="1"
            )
            assert resp.status_code == 200

        assert self._get_slot_count(app, user_id) == 5

        # 6th should be rejected
        self._add_closed_class_status(
            app, subject="DEPT", catalog="99999", section="1"
        )
        resp = self._watch_class(
            client, subject="DEPT", catalog="99999", section="1"
        )
        assert resp.status_code == 200
        assert b"Limit reached" in resp.data
        assert self._get_slot_count(app, user_id) == 5

    def test_untrack_class_decreases_slot_count(self, app, client):
        self._add_closed_class_status(app)
        self._watch_class(client)

        with app.app_context():
            user_id = User.query.first().id
            wc = WatchedClass.query.filter_by(user_id=user_id).first()
            watch_id = wc.id

        assert self._get_slot_count(app, user_id) == 1
        resp = client.delete(f"/unwatch/{watch_id}")
        assert resp.status_code == 200
        assert self._get_slot_count(app, user_id) == 0
        assert b"Removed" in resp.data

    def test_duplicate_track_does_not_increase_count(self, app, client):
        self._add_closed_class_status(app)
        self._watch_class(client)
        with app.app_context():
            user_id = User.query.first().id

        assert self._get_slot_count(app, user_id) == 1

        # Track the same class again
        self._watch_class(client)
        assert self._get_slot_count(app, user_id) == 1

    def test_cannot_track_open_class(self, app, client):
        """Tracking an Open class should return a 'go enroll now' toast."""
        with app.app_context():
            cs = ClassStatus(
                subject="CMSC", catalog_number="15100", section="1",
                term="2264", course_name="Intro CS", enrolled=30, capacity=50,
                status="Open", last_checked=datetime.now(timezone.utc),
                last_changed=datetime.now(timezone.utc),
            )
            db.session.add(cs)
            db.session.commit()

        resp = client.post("/watch", data={
            "subject": "CMSC",
            "catalog_number": "15100",
            "section": "1",
            "term": "2264",
        })
        assert resp.status_code == 200
        assert b"go enroll now" in resp.data

        with app.app_context():
            user_id = User.query.first().id
        assert self._get_slot_count(app, user_id) == 0


# ---------------------------------------------------------------------------
# 3. Closed -> Open notification flow (background job logic)
# ---------------------------------------------------------------------------

class TestClosedToOpenNotification:
    """
    Simulate the check_watched_classes background job detecting a
    Closed -> Open transition, verifying notify_user is called and a
    Notification record is created.
    """

    def test_closed_to_open_triggers_notification(self, app, seed_user):
        user_id = seed_user("alice", "alice@uchicago.edu")

        with app.app_context():
            # Create a Closed ClassStatus
            cs = ClassStatus(
                subject="ECON", catalog_number="20100", section="1",
                term="2264", course_name="Elements of Econ II",
                enrolled=55, capacity=55, status="Closed",
                last_checked=datetime.now(timezone.utc),
                last_changed=datetime.now(timezone.utc),
            )
            db.session.add(cs)
            db.session.commit()
            cs_id = cs.id

            # User watches this class
            wc = WatchedClass(
                user_id=user_id, subject="ECON", catalog_number="20100",
                section="1", term="2264",
            )
            db.session.add(wc)
            db.session.commit()

        # Simulate what check_watched_classes does on a Closed->Open transition
        with app.app_context():
            cs = db.session.get(ClassStatus, cs_id)
            old_status = cs.status  # "Closed"

            # Scraper returns new data: class is now Open
            new_data = {
                "section": "1",
                "course_name": "Elements of Econ II",
                "enrolled": 54,
                "capacity": 55,
                "status": "Open",
                "instructor": "Afonso",
                "schedule": "Mon Wed : 01:30 PM-02:50 PM",
                "class_nbr": "21669",
            }

            # Update ClassStatus
            now = datetime.now(timezone.utc)
            cs.enrolled = new_data["enrolled"]
            cs.capacity = new_data["capacity"]
            cs.status = new_data["status"]
            cs.last_checked = now
            cs.last_changed = now
            db.session.flush()

            # Detect transition and notify
            assert old_status == "Closed"
            assert new_data["status"] == "Open"

            watchers = WatchedClass.query.filter_by(
                subject="ECON", catalog_number="20100", section="1", term="2264"
            ).all()
            assert len(watchers) == 1

            with patch("notifier.requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.raise_for_status.return_value = None
                mock_resp.status_code = 200
                mock_post.return_value = mock_resp

                for w in watchers:
                    user = db.session.get(User, w.user_id)
                    assert user is not None
                    assert user.email == "alice@uchicago.edu"

                    success = notify_user(
                        app.config,
                        user.email,
                        "ECON", "20100", "1",
                        "Elements of Econ II", 54, 55,
                    )
                    assert success is True

                    notif = Notification(
                        user_id=user.id, class_status_id=cs.id,
                        message="ECON 20100 Sec 1 is now Open (54/55)",
                    )
                    db.session.add(notif)

                db.session.commit()

                # Verify notify_user was called (via the Resend mock)
                mock_post.assert_called_once()

            # Verify Notification record exists
            notifs = Notification.query.filter_by(user_id=user_id).all()
            assert len(notifs) == 1
            assert "Open" in notifs[0].message
            assert notifs[0].class_status_id == cs_id


# ---------------------------------------------------------------------------
# 4. Email sending tests (mock Resend API)
# ---------------------------------------------------------------------------

class TestResendEmailSending:
    """Test _send_via_resend and notify_user with mocked requests.post."""

    RESEND_SETTINGS = {
        "provider": "resend",
        "from_email": "alerts@example.com",
        "resend_api_key": "re_test_key_123",
        "reply_to": "",
    }

    @patch("notifier.requests.post")
    def test_resend_payload_correct(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = _send_via_resend(
            self.RESEND_SETTINGS,
            "student@uchicago.edu",
            "Seat Available: ECON 20100",
            "ECON 20100 Section 1 is now OPEN!",
            html_body="<p>ECON 20100 Section 1 is now <strong>OPEN</strong>!</p>",
        )

        assert result is True
        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args
        url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs.get("url")
        assert url == "https://api.resend.com/emails"

        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["to"] == ["student@uchicago.edu"]
        assert payload["subject"] == "Seat Available: ECON 20100"
        assert "Add/Drop Alerts" in payload["from"]
        assert "alerts@example.com" in payload["from"]
        assert payload["text"] == "ECON 20100 Section 1 is now OPEN!"
        assert "<p>" in payload["html"]

        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["Authorization"] == "Bearer re_test_key_123"

    @patch("notifier.requests.post")
    def test_resend_api_failure_returns_false(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("500 Internal Server Error")
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        result = _send_via_resend(
            self.RESEND_SETTINGS,
            "student@uchicago.edu",
            "Seat Available: ECON 20100",
            "body text",
        )
        assert result is False

    @patch("notifier.requests.post")
    def test_notify_user_uses_resend_end_to_end(self, mock_post, app):
        """notify_user with resend config calls Resend API with correct args."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        with app.app_context():
            success = notify_user(
                app.config,
                "student@uchicago.edu",
                "MATH", "16300", "2",
                "Honors Calculus III", 20, 25,
                app_url="https://addrop.example.com",
            )

        assert success is True
        mock_post.assert_called_once()

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["to"] == ["student@uchicago.edu"]
        assert "MATH 16300" in payload["subject"]
        assert "Add/Drop Alerts" in payload["from"]
        # HTML body should contain enrollment info and untrack link
        assert "20/25" in payload["html"]
        assert "addrop.example.com" in payload["html"]

    @patch("notifier.requests.post")
    def test_notify_user_no_email_returns_false(self, mock_post, app):
        with app.app_context():
            result = notify_user(app.config, "", "ECON", "20100", "1", "Test", 0, 0)
        assert result is False
        mock_post.assert_not_called()

    @patch("notifier.requests.post")
    def test_resend_display_name_wrapping(self, mock_post):
        """Bare email address gets wrapped with 'Add/Drop Alerts' display name."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        settings = dict(self.RESEND_SETTINGS)
        settings["from_email"] = "noreply@addrop.app"

        _send_via_resend(settings, "x@y.com", "Subject", "Body")
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["from"] == "Add/Drop Alerts <noreply@addrop.app>"

    @patch("notifier.requests.post")
    def test_resend_already_formatted_from_not_double_wrapped(self, mock_post):
        """If from_email already has <>, don't re-wrap it."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        settings = dict(self.RESEND_SETTINGS)
        settings["from_email"] = "Custom Name <custom@addrop.app>"

        _send_via_resend(settings, "x@y.com", "Subject", "Body")
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["from"] == "Custom Name <custom@addrop.app>"
