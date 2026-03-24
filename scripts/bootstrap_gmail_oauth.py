from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
import threading
import webbrowser
from urllib.parse import urlparse

from google_auth_oauthlib.flow import Flow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config  # noqa: E402
from notifier import SCOPES  # noqa: E402


def required_value(name, fallback=""):
    value = (Config.__dict__.get(name, fallback) or "").strip()
    if not value:
        print(f"Missing required setting: {name}")
        raise SystemExit(1)
    return value


def token_file_path():
    raw_path = (Config.__dict__.get("GMAIL_TOKEN_FILE", "token.json") or "").strip()
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def build_flow(redirect_uri):
    client_id = (Config.__dict__.get("GMAIL_CLIENT_ID") or Config.__dict__.get("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = (Config.__dict__.get("GMAIL_CLIENT_SECRET") or Config.__dict__.get("GOOGLE_CLIENT_SECRET") or "").strip()
    token_uri = (Config.__dict__.get("GMAIL_TOKEN_URI") or "https://oauth2.googleapis.com/token").strip()

    if not client_id or not client_secret:
        print("Missing Google OAuth client settings.")
        raise SystemExit(1)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": token_uri,
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = redirect_uri
    return flow


class CallbackServer:
    def __init__(self, redirect_uri):
        parsed = urlparse(redirect_uri)
        self.redirect_uri = redirect_uri
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 80
        self.path = parsed.path or "/"
        self.authorization_response = None
        self.httpd = None
        self.ready = threading.Event()

    def start(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith(server.path):
                    server.authorization_response = f"http://{self.headers['Host']}{self.path}"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h2>Gmail OAuth complete.</h2><p>You can close this tab and return to the terminal.</p></body></html>"
                    )
                    server.ready.set()
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                return

        self.httpd = HTTPServer((self.host, self.port), Handler)
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        return thread

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


def main():
    redirect_uri = required_value("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:5000/auth/google/callback")
    sender = required_value("GMAIL_SENDER")

    print(f"Using sender account: {sender}")
    print(f"Waiting for OAuth callback at: {redirect_uri}")
    print("Make sure the app server is not already using that same local port.")

    callback_server = CallbackServer(redirect_uri)
    callback_server.start()

    flow = build_flow(redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    print("\nOpen this URL if your browser does not launch automatically:\n")
    print(auth_url)
    print()
    webbrowser.open(auth_url)

    try:
        callback_server.ready.wait()
    except KeyboardInterrupt:
        callback_server.stop()
        print("\nCancelled.")
        raise SystemExit(1)

    callback_server.stop()

    if not callback_server.authorization_response:
        print("OAuth callback did not arrive.")
        raise SystemExit(1)

    flow.fetch_token(authorization_response=callback_server.authorization_response)
    creds = flow.credentials

    token_path = token_file_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())

    print(f"Gmail OAuth is ready. Token saved to {token_path}.")
    if creds.refresh_token:
        print("A refresh token was issued and stored in token.json.")
    else:
        print("No refresh token was returned. Re-run after revoking consent if you need one.")


if __name__ == "__main__":
    main()
