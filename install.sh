#!/usr/bin/env bash

################################################################################
#                                                                              #
#  install.sh — автоматическая установка/обновление окружения Contour App    #
#                                                                              #
#  Скрипт выполняет всё «в одну команду»:                                      #
#   • настраивает репозиторий Docker (CE)                                     #
#   • устанавливает требуемые пакеты (docker-ce, плагины, git и утилиты)     #
#   • проверяет версии Docker/Compose                                          #
#   • клонирует или обновляет репозиторий в /opt/contour-app                    #
#   • делает chmod +x для всех скриптов                                        #
#   • формирует .env (не перезаписывает существующий)                         #
#   • подчищает предыдущие контейнеры и запускает стек в docker compose        #
#   • предлагает включить автообновление (systemd timer)                      #
#                                                                              #
#  Скрипт идемпотентен и безопасен: повторный запуск не повредит               #
#                                                                              #
################################################################################

set -euo pipefail

# цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[contour-install]${NC} $*"; }
log_success() { echo -e "${GREEN}[contour-install]${NC} $*"; }
log_error() { echo -e "${RED}[contour-install] ОШИБКА:${NC} $*" >&2; }
log_warn() { echo -e "${YELLOW}[contour-install]${NC} $*"; }

require_root() {
    if [[ $EUID -ne 0 ]]; then
        if command -v sudo >/dev/null 2>&1; then
            log "Перезапускаем скрипт через sudo..."
            exec sudo bash "$0" "$@"
        fi
        log_error "Запустите скрипт с правами root (sudo)."
        exit 1
    fi
}

check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

version_ge() {
    dpkg --compare-versions "$1" ge "$2"
}

ensure_docker_repo() {
    if ! grep -Rq "download.docker.com" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
        log "Добавляем репозиторий Docker..."
        mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
            | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
            | tee /etc/apt/sources.list.d/docker.list > /dev/null
        log_success "Репозиторий Docker добавлен."
    else
        log "Репозиторий Docker уже настроен."
    fi
}

install_packages() {
    log "Обновляем список пакетов..."
    apt-get update -y

    log "Устанавливаем утилиты для Docker..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        ca-certificates curl gnupg lsb-release || true

    # (репозиторий уже добавлен в ensure_docker_repo)
    log "Обновляем индекс пакетов с репозитория Docker..."
    apt-get update -y

    if check_cmd docker; then
        log "Docker уже установлен, пропускаем установку пакетов Docker."
    else
        log "Устанавливаем Docker и плагины..."
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
            docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin || true
    fi

    # git должен быть установлен независимо
    DEBIAN_FRONTEND=noninteractive apt-get install -y git || true
    # nginx на хосте нам не нужен – всё работает внутри контейнера
}

check_versions() {
    if ! check_cmd docker; then
        log_error "docker не найден после установки."
        exit 1
    fi
    local docker_ver
    docker_ver=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
    if ! version_ge "$docker_ver" "20.0"; then
        log_error "Требуется Docker >=20. Установлена $docker_ver"
        exit 1
    fi
    log "Docker версии $docker_ver OK."

    if check_cmd docker; then
        local compose_ver
        compose_ver=$(docker compose version --short 2>/dev/null || echo "0")
        if ! version_ge "$compose_ver" "2.0"; then
            log_error "Требуется docker compose v2+. Текущая версия: $compose_ver"
            exit 1
        fi
        log "docker compose версии $compose_ver OK."
    fi
}

confirm() {
    local msg="$1"
    read -r -p "${YELLOW}$msg (yes/no): ${NC}" resp
    [[ "$resp" == "yes" ]]
}

start_docker() {
    log "Запуск Docker daemon..."
    # попытаться через systemctl, игнорируем ошибки в контейнерах/LXC
    systemctl enable docker --now 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true

    if ! pgrep -x dockerd >/dev/null 2>&1; then
        log_warn "Docker не запущен системой, стартуем вручную..."
        dockerd > /var/log/dockerd.log 2>&1 &
        sleep 8
    fi

    if ! docker version >/dev/null 2>&1; then
        log_error "Docker не запустился после установки. Смотрите /var/log/dockerd.log"
        exit 1
    fi
    log_success "Docker успешно установлен и работает"
}

main() {
    require_root "$@"
    ensure_docker_repo
    install_packages
    start_docker
    check_versions

    APP_DIR="/opt/contour-app"
    REPO_URL="https://github.com/tvwoth/contour-app.git"
    REPO_BRANCH="${CONTOUR_BRANCH:-main}"

    if [[ -d "$APP_DIR/.git" ]]; then
        log "Репозиторий уже существует, обновляем..."
        cd "$APP_DIR"
        git fetch origin
        git checkout "$REPO_BRANCH" || true
        git pull --ff-only origin "$REPO_BRANCH"
    else
        log "Клонируем репозиторий в $APP_DIR..."
        rm -rf "$APP_DIR"
        git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$APP_DIR"
        cd "$APP_DIR"
    fi

    log "Делаем скрипты исполняемыми..."
    chmod +x *.sh || true

    log "Устанавливаем команды в /usr/local/bin..."
    mkdir -p /usr/local/bin
    ln -sf "$APP_DIR/install.sh" /usr/local/bin/contour-install
    ln -sf "$APP_DIR/update.sh" /usr/local/bin/contour-update
    ln -sf "$APP_DIR/uninstall.sh" /usr/local/bin/contour-uninstall
    log_success "Команды contour-install, contour-update и contour-uninstall доступны глобально."

    read -rp "Введите внутренний порт приложения (APP_PORT) [5000]: " APP_PORT
    APP_PORT=${APP_PORT:-5000}
    log "Порт: $APP_PORT"

    # формируем файл окружения только при первом запуске
    if [ ! -f .env ]; then
        log ".env не найден, создаём из примера"
        if [ -f .env.example ]; then
            cp .env.example .env
            # подставляем порт по-умолчанию
            sed -i "s/^APP_PORT=.*$/APP_PORT=${APP_PORT}/" .env
        else
            echo "APP_PORT=${APP_PORT}" > .env
        fi
        log_success ".env создан"
    else
        log ".env уже существует, пропускаем создание"
    fi

    log "Останавливаем любые существующие контейнеры..."
    docker compose down --remove-orphans -v || true

    log "Запуск контейнеров (docker compose up -d --build --force-recreate)..."
    docker compose up -d --build --force-recreate

    local ip
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    ip=${ip:-<SERVER_IP>}
    log_success "Приложение должно быть доступно по http://${ip}"

    if confirm "Включить ежедневное автообновление (contour-update.timer)?"; then
        log "Настраиваем systemd-таймеры..."
        cp contour-update.service contour-update.timer /etc/systemd/system/ || true
        systemctl daemon-reload
        systemctl enable --now contour-update.timer
        log_success "Автообновление включено."
    else
        log "Автообновление не включено."
    fi

    log_success "Установка/обновление завершено."
}

main "$@"

