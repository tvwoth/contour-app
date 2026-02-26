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

log "Пересборка образов..."
docker compose build

log "Применение обновлённых контейнеров..."
docker compose up -d

log "Текущий статус сервисов:"
docker compose ps

