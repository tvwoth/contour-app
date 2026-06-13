#!/usr/bin/env bash

################################################################################
#  change-password.sh — смена пароля администратора конфигураций               #
################################################################################

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[contour-password]${NC} $*"; }
log_success() { echo -e "${GREEN}[contour-password]${NC} $*"; }
log_error() { echo -e "${RED}[contour-password] ОШИБКА:${NC} $*" >&2; }

APP_DIR="${CONTOUR_APP_DIR:-/opt/contour-app}"

if [[ ! -d "$APP_DIR" ]]; then
    APP_DIR="$(cd "$(dirname "$0")" && pwd)"
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
    log_error "Файл .env не найден в $APP_DIR"
    exit 1
fi

read -rsp "Введите новый пароль администратора: " NEW_PW
echo
if [[ -z "$NEW_PW" ]]; then
    log_error "Пароль не может быть пустым."
    exit 1
fi

read -rsp "Повторите пароль: " NEW_PW2
echo
if [[ "$NEW_PW" != "$NEW_PW2" ]]; then
    log_error "Пароли не совпадают."
    exit 1
fi

if grep -q '^CONFIG_ADMIN_PASSWORD=' .env 2>/dev/null; then
    sed -i "s|^CONFIG_ADMIN_PASSWORD=.*$|CONFIG_ADMIN_PASSWORD=${NEW_PW}|" .env
else
    echo "CONFIG_ADMIN_PASSWORD=${NEW_PW}" >> .env
fi

log_success "Пароль администратора обновлён в .env"

read -r -p "${YELLOW}Перезапустить контейнеры сейчас? (yes/no): ${NC}" RESTART
if [[ "$RESTART" == "yes" ]]; then
    docker compose up -d --force-recreate
    log_success "Контейнеры перезапущены."
else
    log "Перезапустите приложение позже: docker compose up -d --force-recreate"
fi
