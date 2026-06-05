# 📊 Contour App

> Веб-приложение на Flask для расчёта и визуализации контуров.  
> Быстрый запуск через Docker, обратный прокси через Nginx, автообновление «из коробки».

---

## 🚀 Быстрый старт (Docker)

Хотите запустить приложение на чистом сервере Ubuntu/Debian? Просто выполните:

```bash
sudo apt update
sudo apt install curl -y
curl -O https://raw.githubusercontent.com/tvwoth/contour-app/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

🔹 В процессе установки вас попросят указать **внутренний порт приложения (`APP_PORT`)** — по умолчанию `5000`.
🔹 После завершения приложение будет доступно в браузере по адресу:

```text
http://SERVER_IP
```

После первого запуска доступны глобальные команды:

```bash
sudo contour-install
sudo contour-update
sudo contour-uninstall

```
contour-app/
├── Dockerfile                 # Образ Python 3.11 (non-root, gunicorn)
├── docker-compose.yml         # Сервисы: app + nginx, restart: always
├── install.sh                 # One-click установка Docker-версии
├── update.sh                  # Обновление из Git + пересборка контейнеров
├── uninstall.sh               # One-click удаление приложения и следов
├── nginx/default.conf         # Reverse proxy: 80 → app:APP_PORT
├── requirements.txt           # Python-зависимости
├── .env.example               # Шаблон для .env (APP_PORT, HOST_HTTP_PORT)
├── app/                       # Python-пакет с приложением
│   ├── __init__.py            # Flask‑приложение
│   ├── calculator/            # Логика расчётов
│   ├── templates/             # HTML-шаблоны
│   ├── static/                # CSS, JS, изображения
│   └── configs/               # Дополнительные конфиги
└── (прочие скрипты и файлы)

```

---

## 🔧 Как работает установка (`install.sh`)

Скрипт теперь полностью автоматизирован и идемпотентен. После одной
команды он подготовит систему, установит всё нужное и запустит
контейнеры, а повторный запуск просто обновит код и образы.

1. Проверяет права root / sudo.
2. На лету добавляет официальный репозиторий Docker (CE) и ключ.
3. Устанавливает или обновляет пакеты:
   `docker-ce`, `docker-ce-cli`, `containerd.io`,
   `docker-buildx-plugin`, `docker-compose-plugin`, `git` и утилиты
   (`curl`, `lsb-release` и др.).
   **Nginx не устанавливается на хосте — он запускается в контейнере.**
4. Проверяет версии Docker (>= 20) и docker compose (v2+);
   если не удовлетворяют — прекращает выполнение.
5. Клонирует/обновляет репозиторий в `/opt/contour-app` (ветка `main`),
   делает `chmod +x` для всех скриптов.
5. Запрашивает порт приложения `APP_PORT` (по умолчанию 5000) и,
   если `.env` ещё не создан, копирует шаблон `.env.example` и
   подставляет значение. Существующий `.env` не перезаписывается.
   Если порт 80 занят, `install.sh` запросит альтернативный хост‑порт
   `HOST_HTTP_PORT` и запомнит его в `.env`.
7. Перед поднятием стека очищает любые орфанные контейнеры
   (`docker compose down --remove-orphans -v`).
8. Собирает и запускает контейнеры:
   `docker compose up -d --build --force-recreate`.
9. При желании включает ежедневный systemd‑таймер
   (`contour-update.timer`) для автообновления.
10. Выводит адрес приложения и подсказки (`docker compose ps`,
    `docker compose logs -f`).

В выводе используются цветные метки `[contour-install]`.

> 💡 Более не требуется вручную chmod‑ить скрипты, устанавливать
> плагины Compose или удалять старые контейнеры — всё это делает
> `install.sh`.

✅ Контейнеры работают с `restart: always` — после перезагрузки
сервера стек автоматически поднимется.

---

## 🔄 Обновление приложения

Самый простой способ обновиться — использовать глобальную команду:

```bash
sudo contour-update
```

Альтернативно можно запустить локальный скрипт из каталога установки:

```bash
cd /opt/contour-app
sudo ./update.sh
```

Теперь `update.sh` делает больше и безопаснее:

- заходит в `/opt/contour-app` (проверяет, что папка есть);
- тянет `git pull --ff-only` и восстанавливает права на скрипты;
- очищает старые контейнеры (`docker compose down --remove-orphans`);
- пересобирает образы (`docker compose build --no-cache`);
- перезапускает стек (`docker compose up -d --force-recreate`);
- выводит статус (`docker compose ps`).

Выполнение сопровождается цветными логами `[contour-update]` и
`trap` выводит ошибку при сбое.

❗ Одного запуска `install.sh` достаточно, он выполняет всё то же,
что и `update.sh`.

### ⏰ Автообновление (опционально)

Для ежедневного автоматического обновления можно использовать systemd-таймеры:

```bash
sudo cp contour-update.service contour-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contour-update.timer
```

📋 Что делают юниты:
- `contour-update.service` — запускает `/opt/contour-app/update.sh`
- `contour-update.timer` — активирует сервис раз в сутки

---

## 📋 Просмотр логов

Находясь в `/opt/contour-app`:

```bash
# Логи приложения (Flask + Gunicorn)
docker compose logs -f app

# Логи Nginx
docker compose logs -f nginx
```

---

## ⚙️ Как изменить порт после установки

1. Остановите стек:
   ```bash
   docker compose down
   ```

2. Отредактируйте `.env`, указав новый порт:
   ```bash
   nano .env
   # APP_PORT=новый_порт
   ```

3. Обновите `nginx/default.conf`, заменив старый порт на новый  
   *(или просто запустите `install.sh` заново и укажите новый порт)*

4. Запустите стек:
   ```bash
   docker compose up -d --build
   ```

> 🌐 Внешний URL останется `http://SERVER_IP` — Nginx продолжает слушать 80-й порт и проксирует запросы на новый внутренний порт.

---

## 🗑 Полное удаление приложения

Для полного удаления приложения со всеми следами установки выполните глобальную команду:

```bash
sudo contour-uninstall
```

Если вы находитесь в каталоге `/opt/contour-app`, можно использовать локальный скрипт:

```bash
cd /opt/contour-app
sudo ./uninstall.sh
```

Скрипт автоматически:
- ✓ Останавливает Docker-контейнеры и удаляет volumes
- ✓ Отключает и удаляет systemd-юниты для автообновления
- ✓ Удаляет директорию `/opt/contour-app`
- ✓ Требует подтверждения перед удалением

**Запустить без подтверждения:**
```bash
sudo ./uninstall.sh --force
```

**Ручная очистка** (если нужна):
```bash
# Удалить конфиг Nginx (если был создан)
sudo rm -f /etc/nginx/sites-enabled/contour*
sudo nginx -t && sudo systemctl reload nginx

# Удалить Docker (если больше не нужен)
sudo apt remove -y docker.io docker-compose docker-compose-plugin
sudo docker system prune -a -f
```

---

> 💬 **Совет**: Все команды в этом руководстве можно копировать и вставлять — они проверены и работают «как есть».  
> 🐳 Приложение полностью контейнеризовано: минимум зависимостей на хосте, максимум предсказуемости.

*Документация актуальна для версии на базе Docker. При возникновении вопросов — проверяйте логи или создавайте issue в репозитории.* 🛠️

