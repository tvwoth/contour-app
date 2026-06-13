#!/bin/sh

echo "Ensuring correct permissions for user_configs..."

chown -R 1000:1000 /app/app/user_configs 2>/dev/null || true
chmod 755 /app/app/user_configs 2>/dev/null || true

exec "$@"
