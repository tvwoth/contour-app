#!/bin/sh

echo "Fixing permissions for /app/app/user_configs..."

# Try to set ownership and permissions; ignore failures
chown -R 1000:1000 /app/app/user_configs 2>/dev/null || true
chmod 755 /app/app/user_configs 2>/dev/null || true

echo "Starting application as appuser (UID 1000)..."

# Drop privileges and execute the CMD as UID 1000 using gosu (Debian/Ubuntu)
if command -v gosu >/dev/null 2>&1; then
	exec gosu 1000:1000 "$@"
fi

# Fallback: run the command as-is
exec "$@"
