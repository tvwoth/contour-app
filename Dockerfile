FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PORT=5000

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app  # repository root; Python path will include this directory
# application code lives inside the `app/` Python package

COPY . /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE ${APP_PORT}

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${APP_PORT:-5000} --workers 3 app:app"]

