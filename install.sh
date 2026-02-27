#!/usr/bin/env bash

set -euo pipefail

REPO_URL="https://github.com/tvwoth/contour-app.git"
REPO_BRANCH="updates"
APP_DIR="/opt/contour-app"

log() {
  echo "[contour-install] $*"
}

fail() {
  echo "[contour-install] ОШИБКА: $*" >&2
  exit 1
}

trap 'fail "Установка прервана из-за ошибки. Проверьте вывод выше."' ERR

if [[ "$(id -u)" -ne 0 ]]; then
  fail "Скрипт должен выполняться от root. Запустите: sudo ./install.sh"
fi

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  ID_LIKE_LOWER=$(echo "${ID_LIKE:-}" | tr '[:upper:]' '[:lower:]')
  ID_LOWER=$(echo "${ID:-}" | tr '[:upper:]' '[:lower:]')
  if [[ "${ID_LOWER}" != "ubuntu" && "${ID_LOWER}" != "debian" && "${ID_LIKE_LOWER}" != *"debian"* && "${ID_LIKE_LOWER}" != *"ubuntu"* ]]; then
    fail "Поддерживаются только Ubuntu/Debian. Обнаружена система: ${ID:-unknown}"
  fi
else
  fail "Не удалось определить дистрибутив (нет /etc/os-release)."
fi

read -rp "Введите внутренний порт приложения (APP_PORT) [5000]: " APP_PORT
APP_PORT=${APP_PORT:-5000}

log "Обновление списка пакетов..."
apt-get update -y

log "Установка Docker и git..."
DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io git

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker не установлен корректно. Проверьте установку пакета docker.io."
fi

COMPOSE_CMD=""
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  log "docker compose не найден, пробую установить docker-compose..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose || true
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
  fi
fi

if [[ -z "${COMPOSE_CMD}" ]]; then
  fail "Не найден ни 'docker compose', ни 'docker-compose'. Установите docker-compose вручную и повторите попытку."
fi

log "Включение и запуск сервиса docker..."
systemctl enable docker
systemctl start docker

if [[ -d "${APP_DIR}/.git" ]]; then
  log "Репозиторий уже существует в ${APP_DIR}, переключаюсь на ветку ${REPO_BRANCH} и обновляю..."
  cd "${APP_DIR}"
  git fetch origin || fail "Не удалось выполнить git fetch в ${APP_DIR}"
  git checkout "${REPO_BRANCH}" || fail "Не удалось переключиться на ветку ${REPO_BRANCH}"
  git pull --ff-only origin "${REPO_BRANCH}" || fail "Не удалось выполнить git pull в ${APP_DIR}"
else
  log "Клонирование репозитория (ветка ${REPO_BRANCH}) в ${APP_DIR}..."
  rm -rf "${APP_DIR}"
  git clone --branch "${REPO_BRANCH}" --single-branch "${REPO_URL}" "${APP_DIR}" || fail "Не удалось клонировать репозиторий"
  cd "${APP_DIR}"
fi

log "Создание файла .env с портом приложения..."
cat > .env <<EOF
APP_PORT=${APP_PORT}
EOF

if grep -q "APP_PORT_PLACEHOLDER" nginx/default.conf 2>/dev/null; then
  log "Подстановка порта в nginx/default.conf..."
  sed -i "s/APP_PORT_PLACEHOLDER/${APP_PORT}/g" nginx/default.conf
fi

log "Остановка и удаление старых контейнеров (если есть)..."
${COMPOSE_CMD} down -v || true

log "Сборка и запуск контейнеров (${COMPOSE_CMD} up -d --build)..."
${COMPOSE_CMD} up -d --build

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
SERVER_IP="${SERVER_IP:-<SERVER_IP>}"

echo
log "УСТАНОВКА ЗАВЕРШЕНА."
echo "Приложение доступно (после запуска контейнеров) по адресу:"
echo "  http://${SERVER_IP}"
echo
echo "Для управления контейнерами из каталога ${APP_DIR}:"
echo "  ${COMPOSE_CMD} ps"
echo "  ${COMPOSE_CMD} logs -f"
echo "  ${COMPOSE_CMD} restart"

