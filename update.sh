#!/usr/bin/env bash

set -euo pipefail

APP_DIR="/opt/contour-app"

log() {
  echo "[contour-update] $*"
}

fail() {
  echo "[contour-update] ОШИБКА: $*" >&2
  exit 1
}

trap 'fail "Обновление прервано из-за ошибки. Проверьте вывод выше."' ERR

if [[ "$(id -u)" -ne 0 ]]; then
  fail "Скрипт должен выполняться от root. Запустите: sudo ./update.sh"
fi

cd "${APP_DIR}" || fail "Каталог ${APP_DIR} не найден"

log "Получение последних изменений из Git..."
git pull --ff-only

COMPOSE_CMD=""
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  fail "Не найден ни 'docker compose', ни 'docker-compose'. Установите docker-compose и повторите попытку."
fi

log "Пересборка образов..."
${COMPOSE_CMD} build

log "Применение обновлённых контейнеров..."
${COMPOSE_CMD} up -d

log "Текущий статус сервисов:"
${COMPOSE_CMD} ps

