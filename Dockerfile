FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PORT=5000

RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/sh -m appuser

WORKDIR /app  # repository root; Python path will include this directory
# application code lives inside the `app/` Python package

COPY requirements.txt /app/

RUN python -m pip install --no-cache-dir --upgrade pip
RUN python -m pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN chown -R appuser:appgroup /app

# Ensure user_configs directory exists inside image and owned by appuser
RUN mkdir -p /app/app/user_configs && chown -R appuser:appgroup /app/app/user_configs

# Install gosu for dropping privileges at container start
RUN apt-get update && apt-get install -y gosu && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app
ENV MPLCONFIGDIR=/tmp/.config/matplotlib

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run entrypoint as root; entrypoint will drop privileges to UID 1000 using gosu
ENTRYPOINT ["/entrypoint.sh"]

EXPOSE ${APP_PORT}

CMD ["sh", "-c", "gunicorn --chdir /app --bind 0.0.0.0:${APP_PORT:-5000} --workers 3 app:app"]

