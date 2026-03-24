import base64
import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
BASE_DIR = Path(__file__).resolve().parent


def _config_value(config, key, default=""):
    if config is None:
        return os.environ.get(key, default)
    return config.get(key, default)


def _config_int(config, key, default):
    value = _config_value(config, key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_flag(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(path_value):
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _gmail_settings(config=None):
    google_client_id = _config_value(config, "GOOGLE_CLIENT_ID", "").strip()
    google_client_secret = _config_value(config, "GOOGLE_CLIENT_SECRET", "").strip()
    return {
        "sender": _config_value(
            config,
            "GMAIL_SENDER",
            _config_value(config, "EMAIL_FROM", ""),
        ).strip(),
        "client_id": _config_value(config, "GMAIL_CLIENT_ID", google_client_id).strip(),
        "client_secret": _config_value(config, "GMAIL_CLIENT_SECRET", google_client_secret).strip(),
        "refresh_token": _config_value(config, "GMAIL_REFRESH_TOKEN", "").strip(),
        "token_uri": _config_value(
            config,
            "GMAIL_TOKEN_URI",
            "https://oauth2.googleapis.com/token",
        ).strip(),
        "credentials_file": _resolve_path(
            _config_value(config, "GMAIL_CREDENTIALS_FILE", "credentials.json").strip()
        ),
        "token_file": _resolve_path(
            _config_value(config, "GMAIL_TOKEN_FILE", "token.json").strip()
        ),
        "interactive_auth": _env_flag(
            _config_value(config, "GMAIL_ENABLE_INTERACTIVE_AUTH", "false")
        ),
    }


def _gmail_notifications_ready(settings):
    if not settings["sender"]:
        return False

    if settings["refresh_token"] and settings["client_id"] and settings["client_secret"]:
        return True

    token_file = settings["token_file"]
    if token_file and token_file.exists():
        return True

    credentials_file = settings["credentials_file"]
    has_client_config = bool(settings["client_id"] and settings["client_secret"])
    return bool(
        settings["interactive_auth"]
        and ((credentials_file and credentials_file.exists()) or has_client_config)
    )


def _email_settings(config=None):
    provider = _config_value(config, "EMAIL_PROVIDER", "").strip().lower()
    if not provider:
        if _config_value(config, "RESEND_API_KEY", "").strip():
            provider = "resend"
        elif _config_value(config, "SMTP_HOST", "").strip():
            provider = "smtp"
        elif (
            _config_value(config, "GMAIL_SENDER", "").strip()
            or _config_value(config, "GMAIL_REFRESH_TOKEN", "").strip()
        ):
            provider = "gmail_api"

    return {
        "provider": provider,
        "from_email": _config_value(
            config,
            "EMAIL_FROM",
            _config_value(config, "GMAIL_SENDER", ""),
        ).strip(),
        "reply_to": _config_value(config, "EMAIL_REPLY_TO", "").strip(),
        "resend_api_key": _config_value(config, "RESEND_API_KEY", "").strip(),
        "smtp_host": _config_value(config, "SMTP_HOST", "").strip(),
        "smtp_port": _config_int(config, "SMTP_PORT", 587),
        "smtp_username": _config_value(config, "SMTP_USERNAME", "").strip(),
        "smtp_password": _config_value(config, "SMTP_PASSWORD", "").strip(),
        "smtp_use_tls": _env_flag(_config_value(config, "SMTP_USE_TLS", "true")),
        "smtp_use_ssl": _env_flag(_config_value(config, "SMTP_USE_SSL", "false")),
        "gmail": _gmail_settings(config),
    }


def notifications_ready(config=None):
    settings = _email_settings(config)
    provider = settings["provider"]

    if provider == "resend":
        return bool(settings["from_email"] and settings["resend_api_key"])

    if provider == "smtp":
        auth_valid = (
            (not settings["smtp_username"] and not settings["smtp_password"])
            or (settings["smtp_username"] and settings["smtp_password"])
        )
        return bool(
            settings["from_email"]
            and settings["smtp_host"]
            and settings["smtp_port"]
            and auth_valid
        )

    if provider == "gmail_api":
        if settings["gmail"]["sender"] != settings["from_email"] and settings["from_email"]:
            settings["gmail"]["sender"] = settings["from_email"]
        return _gmail_notifications_ready(settings["gmail"])

    return False


def notification_sender(config=None):
    return _email_settings(config)["from_email"]


def notification_provider_name(config=None):
    provider = _email_settings(config)["provider"]
    labels = {
        "resend": "Resend",
        "smtp": "SMTP",
        "gmail_api": "Gmail API",
    }
    return labels.get(provider, "")


def gmail_notifications_ready(config=None):
    return notifications_ready(config)


def _load_credentials_from_refresh_token(settings):
    if not (
        settings["refresh_token"]
        and settings["client_id"]
        and settings["client_secret"]
    ):
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=settings["refresh_token"],
            token_uri=settings["token_uri"],
            client_id=settings["client_id"],
            client_secret=settings["client_secret"],
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds
    except Exception as exc:
        logger.error("Failed to refresh Gmail access token from env config: %s", exc)
        return None


def _load_credentials_from_token_file(settings):
    token_file = settings["token_file"]
    if not token_file or not token_file.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    except Exception as exc:
        logger.error("Failed to read Gmail token file %s: %s", token_file, exc)
        return None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
            logger.info("Refreshed Gmail token file")
            return creds
        except Exception as exc:
            logger.error("Failed to refresh Gmail token file %s: %s", token_file, exc)

    return None


def _load_credentials_from_interactive_flow(settings):
    credentials_file = settings["credentials_file"]
    if not settings["interactive_auth"]:
        logger.error(
            "Interactive Gmail OAuth is disabled. "
            "Set GMAIL_ENABLE_INTERACTIVE_AUTH=true for local development "
            "or configure GMAIL_REFRESH_TOKEN for server use."
        )
        return None

    if credentials_file and credentials_file.exists():
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
    elif settings["client_id"] and settings["client_secret"]:
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": settings["client_id"],
                    "client_secret": settings["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": settings["token_uri"],
                }
            },
            SCOPES,
        )
    else:
        logger.error(
            "Interactive Gmail OAuth needs either %s or GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET.",
            credentials_file,
        )
        return None

    creds = flow.run_local_server(port=0)

    token_file = settings["token_file"]
    if token_file:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json())
        logger.info("Gmail OAuth token saved to %s", token_file)

    return creds


def _get_gmail_service(settings):
    if not settings["sender"]:
        logger.error("Missing GMAIL_SENDER. Email notifications are disabled.")
        return None

    creds = _load_credentials_from_refresh_token(settings)
    if not creds:
        creds = _load_credentials_from_token_file(settings)
    if not creds and settings["interactive_auth"]:
        creds = _load_credentials_from_interactive_flow(settings)

    if not creds:
        logger.error(
            "Gmail notifications are not configured. "
            "Set GMAIL_SENDER plus GMAIL_REFRESH_TOKEN (recommended), "
            "or use token.json/credentials.json for local development."
        )
        return None

    return build("gmail", "v1", credentials=creds)


def get_gmail_service(config=None):
    """Authenticate with Gmail API using OAuth2. Returns a Gmail service object."""
    return _get_gmail_service(_gmail_settings(config))


def _seat_opening_message(subject_code, catalog_number, section, course_name, enrolled, capacity):
    subject = f"Seat Available: {subject_code} {catalog_number}"
    enroll_url = "https://portal.uchicago.edu/ais/"
    text_body = (
        f"{subject_code} {catalog_number} Section {section} is now OPEN!\n\n"
        f"{course_name}\n"
        f"Enrollment: {enrolled}/{capacity}\n\n"
        f"Log in to enroll before it fills up: {enroll_url}"
    )
    html_body = (
        f"<p><strong>{subject_code} {catalog_number} Section {section}</strong> is now OPEN!</p>"
        f"<p>{course_name}<br>Enrollment: {enrolled}/{capacity}</p>"
        f'<p><a href="{enroll_url}" style="color:#800000;font-weight:bold;">'
        f"Log in to enroll before it fills up</a></p>"
    )
    return subject, text_body, html_body


def _build_message(sender_email, to_email, subject, body, reply_to="", html_body=""):
    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = sender_email
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    return msg


def _send_via_resend(settings, to_email, subject, body, html_body=""):
    # Wrap bare addresses with a friendly display name
    from_addr = settings["from_email"]
    if "<" not in from_addr:
        from_addr = f"Add/Drop Alerts <{from_addr}>"

    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if html_body:
        payload["html"] = html_body
    if settings["reply_to"]:
        payload["reply_to"] = settings["reply_to"]

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings['resend_api_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        logger.info("Email sent via Resend to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email via Resend to %s: %s", to_email, exc)
        return False


def _send_via_smtp(settings, to_email, subject, body, html_body=""):
    msg = _build_message(
        settings["from_email"],
        to_email,
        subject,
        body,
        settings["reply_to"],
        html_body,
    )

    try:
        if settings["smtp_use_ssl"]:
            server = smtplib.SMTP_SSL(
                settings["smtp_host"],
                settings["smtp_port"],
                timeout=20,
            )
        else:
            server = smtplib.SMTP(
                settings["smtp_host"],
                settings["smtp_port"],
                timeout=20,
            )

        with server:
            if not settings["smtp_use_ssl"]:
                server.ehlo()
            if settings["smtp_use_tls"] and not settings["smtp_use_ssl"]:
                server.starttls()
                server.ehlo()
            if settings["smtp_username"] or settings["smtp_password"]:
                server.login(settings["smtp_username"], settings["smtp_password"])
            server.send_message(msg)
        logger.info("Email sent via SMTP to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email via SMTP to %s: %s", to_email, exc)
        return False


def _send_via_gmail(settings, to_email, subject, body, html_body=""):
    service = _get_gmail_service(settings)
    if not service:
        logger.error("Gmail service not available — cannot send notification")
        return False

    msg = _build_message(
        settings["sender"],
        to_email,
        subject,
        body,
        _config_value(settings, "reply_to", ""),
        html_body,
    )
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        logger.info("Email sent via Gmail API to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email via Gmail API to %s: %s", to_email, exc)
        return False


def notify_user(config, to_email, subject_code, catalog_number, section, course_name, enrolled, capacity):
    """Send an email notification when a seat opens up."""
    if not to_email:
        logger.warning("No email address for user, skipping notification")
        return False

    settings = _email_settings(config)
    if not settings["from_email"]:
        logger.warning("No notification sender configured, skipping notification")
        return False

    if not notifications_ready(config):
        logger.error("Email notifications are not configured for provider '%s'", settings["provider"])
        return False

    subject, body, html_body = _seat_opening_message(
        subject_code,
        catalog_number,
        section,
        course_name,
        enrolled,
        capacity,
    )

    provider = settings["provider"]
    if provider == "resend":
        return _send_via_resend(settings, to_email, subject, body, html_body)
    if provider == "smtp":
        return _send_via_smtp(settings, to_email, subject, body, html_body)
    if provider == "gmail_api":
        gmail_settings = dict(settings["gmail"])
        gmail_settings["sender"] = settings["from_email"]
        gmail_settings["reply_to"] = settings["reply_to"]
        return _send_via_gmail(gmail_settings, to_email, subject, body, html_body)

    logger.error(
        "Unsupported EMAIL_PROVIDER '%s'. Use 'resend', 'smtp', or 'gmail_api'.",
        provider,
    )
    return False
