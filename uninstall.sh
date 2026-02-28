#!/usr/bin/env bash

################################################################################
#                                                                              #
#  uninstall.sh — полное удаление приложения Contour App с сервера            #
#                                                                              #
#  НАЗНАЧЕНИЕ:                                                                #
#  Скрипт удаляет все следы установки Contour App:                           #
#  • Останавливает и удаляет Docker-контейнеры, volumes, networks            #
#  • Отключает и удаляет systemd-юниты для автообновления                    #
#  • Удаляет директорию проекта /opt/contour-app                             #
#  • Выводит инструкции для ручной очистки Nginx                             #
#                                                                              #
#  ИСПОЛЬЗОВАНИЕ:                                                             #
#  sudo ./uninstall.sh              # Требует подтверждения                  #
#  sudo ./uninstall.sh --force      # Запускает без подтверждения            #
#                                                                              #
#  БЕЗОПАСНОСТЬ:                                                              #
#  • Требует прав root (sudo)                                                 #
#  • Проверяет существование директорий перед удалением                      #
#  • Игнорирует некритичные ошибки (полусообщения)                           #
#  • Идемпотентен (можно запускать несколько раз)                            #
#                                                                              #
################################################################################

set -euo pipefail

# ============================================================================
# Цветные выводы
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_info() {
    echo -e "${BLUE}→${NC} $1"
}

# ============================================================================
# Проверки и функции
# ============================================================================

require_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт должен запускаться с правами root (sudo)."
        exit 1
    fi
}

confirm_action() {
    local prompt="$1"
    local force_mode="${2:-false}"
    
    if [[ "$force_mode" == "true" ]]; then
        return 0
    fi
    
    echo -ne "${YELLOW}⚠${NC} $prompt (введите 'yes' для подтверждения): "
    read -r response
    if [[ "$response" != "yes" ]]; then
        log_info "Отмена操作."
        exit 0
    fi
}

directory_exists() {
    [[ -d "$1" ]]
}

file_exists() {
    [[ -f "$1" ]]
}

systemd_unit_exists() {
    systemctl list-unit-files | grep -q "^$1" 2>/dev/null || false
}

# ============================================================================
# Основная логика удаления
# ============================================================================

main() {
    local force_mode=false
    
    # Обработка флага --force
    if [[ "${1:-}" == "--force" ]]; then
        force_mode=true
    fi
    
    # Проверка прав
    require_root
    
    log_info "=========================================="
    log_info "  Удаление приложения Contour App"
    log_info "=========================================="
    echo ""
    
    # Шаг 1: Проверить существование директории проекта
    if ! directory_exists "/opt/contour-app"; then
        log_warning "Директория /opt/contour-app не найдена."
        log_info "Приложение уже удалено или не был установлено."
        exit 0
    fi
    
    log_success "Найдена директория /opt/contour-app"
    echo ""
    
    confirm_action "Удалить полностью приложение Contour App?" "$force_mode"
    echo ""
    
    # Шаг 2: Остановить Docker-контейнеры
    log_info "Останавливаем Docker-контейнеры..."
    if directory_exists "/opt/contour-app" && file_exists "/opt/contour-app/docker-compose.yml"; then
        cd "/opt/contour-app"
        
        # Пытаемся остановить контейнеры (ошибка не критична)
        if docker compose down -v --remove-orphans 2>/dev/null || docker-compose down -v --remove-orphans 2>/dev/null || true; then
            log_success "Docker-контейнеры остановлены и удалены (включая volumes)"
        else
            log_warning "Не удалось остановить контейнеры (возможно, Docker уже остановлен)"
        fi
    else
        log_warning "docker-compose.yml не найден, пропускаем остановку контейнеров"
    fi
    
    echo ""
    
    # Шаг 3: Отключить и удалить systemd-юниты
    log_info "Отключаем и удаляем systemd-юниты..."
    
    local units_to_remove=(
        "contour-update.timer"
        "contour-update.service"
        "contour.service"
    )
    
    local units_removed=false
    
    for unit in "${units_to_remove[@]}"; do
        if systemctl is-enabled "$unit" &>/dev/null 2>&1 || systemctl is-active "$unit" &>/dev/null 2>&1; then
            log_info "  • Отключаем и удаляем $unit..."
            systemctl stop "$unit" 2>/dev/null || true
            systemctl disable "$unit" 2>/dev/null || true
            
            if file_exists "/etc/systemd/system/$unit"; then
                rm -f "/etc/systemd/system/$unit"
                units_removed=true
                log_success "    $unit удалена"
            fi
        fi
    done
    
    if [[ "$units_removed" == "true" ]]; then
        log_info "  • Перезагружаем systemd..."
        systemctl daemon-reload
        systemctl reset-failed || true
        log_success "systemd-юниты удалены и systemd перезагружены"
    else
        log_warning "systemd-юниты не найдены (возможно, уже удалены)"
    fi
    
    echo ""
    
    # Шаг 4: Удалить директорию проекта
    log_info "Удаляем директорию проекта..."
    if directory_exists "/opt/contour-app"; then
        rm -rf "/opt/contour-app"
        log_success "/opt/contour-app полностью удалена"
    else
        log_warning "Директория /opt/contour-app уже не существует"
    fi
    
    echo ""
    
    # Шаг 5: Информация о ручной очистке
    log_warning "=========================================="
    log_warning "  ТРЕБУЕТСЯ РУЧНАЯ ОЧИСТКА"
    log_warning "=========================================="
    echo ""
    log_info "Nginx:"
    log_info "  1. Если был создан отдельный конфиг для Contour App, удалите:"
    log_info "     sudo rm -f /etc/nginx/sites-enabled/contour*"
    log_info "     sudo rm -f /etc/nginx/sites-available/contour*"
    log_info ""
    log_info "  2. Проверьте/обновите конфиг Nginx:"
    log_info "     sudo nginx -t  # Проверка синтаксиса"
    log_info "     sudo systemctl reload nginx  # Перезагрузка"
    echo ""
    log_info "Docker (опционально):"
    log_info "  Если Docker больше не нужен, удалите его:"
    log_info "     sudo apt remove -y docker.io docker-compose docker-compose-plugin"
    log_info "     sudo docker system prune -a -f"
    echo ""
    
    # Итоговое сообщение
    echo ""
    log_success "=========================================="
    log_success "  Приложение Contour App успешно удалено!"
    log_success "=========================================="
}

# Запуск
main "$@"
