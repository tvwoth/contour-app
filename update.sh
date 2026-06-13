#!/usr/bin/env bash

################################################################################
#                                                                              #
#  update.sh — безопасное обновление контейнеризированного приложения         #
#                                                                              #
#  Действует idempotentно:                                                      #
#   • проверяет root                                                           #
#   • скачивает свежий код из Git                                               #
#   • восстанавливает права на скрипты                                         #
#   • очищает старые контейнеры, чтобы избежать конфликтов                     #
#   • пересобирает и перезапускает стек                                          #
#                                                                              #
################################################################################

set -euo pipefail

# цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[contour-update]${NC} $*"; }
log_success() { echo -e "${GREEN}[contour-update]${NC} $*"; }
log_error() { echo -e "${RED}[contour-update] ОШИБКА:${NC} $*" >&2; }

require_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Скрипт должен запускаться от root."
        exit 1
    fi
}

trap 'log_error "Обновление прервано."' ERR

main() {
    require_root
    APP_DIR="/opt/contour-app"

    if [[ ! -d "$APP_DIR" ]]; then
        log_error "Каталог $APP_DIR не найден."
        exit 1
    fi

    cd "$APP_DIR"
    log "Получаем последние изменения из Git..."
    git pull --ff-only || true

    log "Делаем скрипты исполняемыми..."
    chmod +x *.sh || true

    if [[ -f .env ]] && ! grep -q '^CONFIG_ADMIN_PASSWORD=' .env 2>/dev/null; then
        read -rsp "Пароль администратора отсутствует. Введите пароль (Enter = admin): " ADMIN_PW
        echo
        ADMIN_PW=${ADMIN_PW:-admin}
        echo "CONFIG_ADMIN_PASSWORD=${ADMIN_PW}" >> .env
        log_success "Пароль администратора добавлен в .env"
    fi

    if [[ -f .env ]] && ! grep -q '^SECRET_KEY=' .env 2>/dev/null; then
        SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "SECRET_KEY=${SECRET_KEY}" >> .env
        log "SECRET_KEY сгенерирован для сессий Flask"
    fi

    mkdir -p data/user_configs

    ln -sf "$APP_DIR/change-password.sh" /usr/local/bin/contour-change-password 2>/dev/null || true

    log "Останавливаем старые контейнеры и очищаем..."
    docker compose down --remove-orphans || true

    log "Собираем образы и перезапускаем стек..."
    docker compose up -d --build --force-recreate

    log "Текущий статус:"
    docker compose ps || true

    log_success "Обновление завершено."
}

main "$@"
