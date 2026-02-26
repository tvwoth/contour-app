#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${APP_DIR}/venv"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Виртуальное окружение не найдено по пути: ${VENV_DIR}" >&2
  echo "Создайте окружение командой: python3 -m venv venv и установите зависимости." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

export PYTHONUNBUFFERED=1

cd "${APP_DIR}"

exec gunicorn --bind 0.0.0.0:5000 --workers 3 app:app

