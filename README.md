# Add/Drop

Flask app for tracking UChicago class availability and notifying users when seats open.

## Environment

The app reads configuration from environment variables.

Key variables:

- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`: Google Sign-In for users
- `EMAIL_PROVIDER`: notification delivery backend
- `EMAIL_FROM`: app-owned sender address such as `alerts@yourdomain.com`
- `GOOGLE_OAUTH_REDIRECT_URI`: optional explicit callback URL for deployed environments

## Google Sign-In

Create a Google OAuth client for your app and set:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

If your deployment sits behind a proxy or custom domain, also set:

```bash
export GOOGLE_OAUTH_REDIRECT_URI="https://your-domain.example/auth/google/callback"
```

For local development, the app is set up to use:

```bash
http://localhost:5000/auth/google/callback
```

Make sure that exact URL is added to your Google OAuth client's authorized redirect URIs.

## Email Notifications

Recommended production setup:

1. Use an app-owned sender such as `alerts@yourdomain.com`.
2. Connect a transactional provider. The app supports `resend` and `smtp`.
3. Set:

```bash
export EMAIL_PROVIDER="resend"
export EMAIL_FROM="alerts@yourdomain.com"
export EMAIL_REPLY_TO="support@yourdomain.com"
export RESEND_API_KEY="re_xxx"
```

SMTP alternative:

```bash
export EMAIL_PROVIDER="smtp"
export EMAIL_FROM="alerts@yourdomain.com"
export SMTP_HOST="smtp.your-provider.com"
export SMTP_PORT="587"
export SMTP_USERNAME="smtp-user"
export SMTP_PASSWORD="smtp-password"
export SMTP_USE_TLS="true"
```

Legacy Gmail API fallback:

```bash
export EMAIL_PROVIDER="gmail_api"
export GMAIL_SENDER="you@gmail.com"
export GMAIL_REFRESH_TOKEN="your-refresh-token"
```

If you use the Gmail fallback, `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` can reuse the Google Sign-In client if you want. If you leave them blank, the app falls back to `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

Local-only Gmail fallback:

- Place `credentials.json` in the project root
- Set `GMAIL_ENABLE_INTERACTIVE_AUTH=true`
- The app can create `token.json` after a browser consent flow

That interactive Gmail flow is intended for local development, not deployment.

You can bootstrap that local Gmail consent flow explicitly with:

```bash
python3 scripts/bootstrap_gmail_oauth.py
```

That helper uses `GOOGLE_OAUTH_REDIRECT_URI`, so the local Flask app should not already be running on that same port while you bootstrap Gmail.

## Running

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

For Docker:

```bash
docker build -t add-drop .
docker run --env-file .env -p 8080:8080 add-drop
```
