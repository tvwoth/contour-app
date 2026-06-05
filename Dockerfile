FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PORT=5000

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app  # repository root; Python path will include this directory
# application code lives inside the `app/` Python package

COPY requirements.txt /app/

RUN python -m pip install --no-cache-dir --upgrade pip
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN chown -R appuser:appgroup /app

USER appuser

ENV PYTHONPATH=/app
ENV MPLCONFIGDIR=/tmp/.config/matplotlib

EXPOSE ${APP_PORT}

CMD ["sh", "-c", "gunicorn --chdir /app --bind 0.0.0.0:${APP_PORT:-5000} --workers 3 app:app"]

