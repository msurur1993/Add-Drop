FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget gnupg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user before installing Playwright
RUN useradd -m -r appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright as appuser so browser cache is accessible
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
RUN playwright install chromium && playwright install-deps
RUN chown -R appuser:appuser /app /home/appuser

USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "--workers", "1", "app:app"]
