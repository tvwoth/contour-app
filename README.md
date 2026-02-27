Contour App
===========

Веб-приложение на Flask для расчёта и визуализации контура с использованием библиотеки Matplotlib.

Приложение запускает HTTP-сервер на порту 5000 и отрисовывает график по введённым пользователем параметрам.

=============================
QUICK INSTALL (DOCKER VERSION)
=============================

Для быстрой установки на чистый сервер Ubuntu/Debian выполните:

```bash
sudo apt update
sudo apt install curl -y
curl -O https://raw.githubusercontent.com/tvwoth/contour-app/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

В процессе установки вас спросят **внутренний порт приложения (APP_PORT)**, по умолчанию `5000`.
Снаружи приложение доступно по HTTP на 80‑м порту:

```text
http://SERVER_IP
```

Где `SERVER_IP` — IP-адрес вашего сервера (например, можно посмотреть через `hostname -I`).

Структура проекта
-----------------

- `Dockerfile` — образ приложения на Python 3.11 (non‑root, gunicorn).
- `docker-compose.yml` — сервисы `app` и `nginx`, сеть bridge, `restart: always`.
- `install.sh` — автоустановка Docker‑версии (one‑click, Ubuntu/Debian).
- `update.sh` — автообновление из Git с пересборкой контейнеров.
- `nginx/default.conf` — конфиг reverse proxy (80 → app:APP_PORT).
- `requirements.txt` — Python‑зависимости.
- `.env.example` — пример `.env` с `APP_PORT`.
- `app.py` — точка входа Flask‑приложения (`app:app`), dev‑порт 5000.
- Остальной код (`calculator/`, `templates/`, `static/`, `configs/`) — логика и ресурсы приложения.

Как работает установка (Docker)
-------------------------------

Скрипт `install.sh` выполняет следующие шаги:

- **Проверка ОС**: убеждается, что система — Ubuntu/Debian.
- **Выбор порта**: спрашивает у пользователя `APP_PORT` (внутренний порт приложения, по умолчанию `5000`).
- **Установка Docker и docker compose plugin**: ставит `docker.io`, `docker-compose-plugin`, `git`.
- **Клонирование репозитория**: клонирует `contour-app` в `/opt/contour-app` или обновляет `git pull`.
- **Создание `.env`**: формирует файл `.env` с выбранным `APP_PORT`.
- **Настройка Nginx**: подставляет выбранный порт в `nginx/default.conf` вместо `APP_PORT_PLACEHOLDER`.
- **Запуск Docker‑стека**: выполняет `docker compose up -d --build`, поднимая контейнеры `app` и `nginx`.
- **Вывод адреса**: показывает URL вида `http://SERVER_IP`.

Контейнеры работают под управлением Docker с политикой `restart: always`, поэтому после перезагрузки сервера стек поднимется автоматически (при запущенном `docker`).

UPDATE (обновление)
-------------------

Для обновления приложения (получение новых версий из Git и пересборка контейнеров) на сервере выполните:

```bash
sudo ./update.sh
```

Скрипт `update.sh`:

- Переходит в `/opt/contour-app`.
- Делает `git pull --ff-only`.
- Выполняет `docker compose build` и `docker compose up -d`.
- Показывает статус контейнеров (`docker compose ps`). 

Для автоматического ежедневного обновления можно использовать systemd‑таймеры из репозитория:

- `contour-update.service` — запускает `/opt/contour-app/update.sh` один раз.
- `contour-update.timer` — планирует запуск `contour-update.service` раз в сутки.

Пример активации автообновления:

```bash
sudo cp contour-update.service contour-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contour-update.timer
```

Просмотр логов (Docker)
------------------------

Из каталога `/opt/contour-app`:

- Логи приложения (gunicorn + Flask):

  ```bash
  docker compose logs -f app
  ```

- Логи Nginx:

  ```bash
  docker compose logs -f nginx
  ```

Как поменять порт после установки
---------------------------------

1. Остановите стек (из `/opt/contour-app`):

   ```bash
   docker compose down
   ```

2. Измените значение `APP_PORT` в `.env`:

   ```bash
   nano .env
   # APP_PORT=новый_порт
   ```

3. Обновите `nginx/default.conf`, заменив старое значение порта на новое (или снова запустите `install.sh` и выберите другой порт).
4. Поднимите стек заново:

   ```bash
   docker compose up -d --build
   ```

Снаружи URL останется `http://SERVER_IP`, так как Nginx слушает 80‑й порт и проксирует запросы на внутренний порт приложения.

Как удалить приложение с сервера
--------------------------------

1. Остановите и удалите контейнеры и тома (из `/opt/contour-app`):

   ```bash
   docker compose down -v
   ```

2. (Опционально) Отключите автообновление, если включали его ранее:

   ```bash
   sudo systemctl disable --now contour-update.timer || true
   sudo systemctl disable contour-update.service || true
   sudo rm -f /etc/systemd/system/contour-update.service /etc/systemd/system/contour-update.timer
   sudo systemctl daemon-reload
   ```

3. Удалите директорию приложения:

   ```bash
   sudo rm -rf /opt/contour-app
   ```

4. (Опционально) Если Docker больше не нужен на этом сервере, вы можете удалить его и связанные данные:

   ```bash
   sudo apt remove -y docker.io docker-compose docker-compose-plugin || true
   sudo docker system prune -a -f || true
   ```

