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

> 💡 `SERVER_IP` — внешний IP-адрес вашего сервера. Узнать его можно командой `hostname -I`.

---

## 🗂 Структура проекта

```
contour-app/
├── Dockerfile                 # Образ Python 3.11 (non-root, gunicorn)
├── docker-compose.yml         # Сервисы: app + nginx, restart: always
├── install.sh                 # One-click установка Docker-версии
├── update.sh                  # Обновление из Git + пересборка контейнеров
├── nginx/default.conf         # Reverse proxy: 80 → app:APP_PORT
├── requirements.txt           # Python-зависимости
├── .env.example               # Шаблон для .env (APP_PORT)
├── app.py                     # Точка входа Flask (dev-порт 5000)
├── calculator/                # Логика расчётов
├── templates/                 # HTML-шаблоны
├── static/                    # CSS, JS, изображения
└── configs/                   # Дополнительные конфиги
```

---

## 🔧 Как работает установка (`install.sh`)

Скрипт делает всё за вас:

1. **Проверяет ОС** — работает только на Ubuntu/Debian.
2. **Запрашивает порт** — вы указываете `APP_PORT` (внутренний, по умолчанию `5000`).
3. **Устанавливает зависимости** — `docker.io`, `docker-compose-plugin`, `git`.
4. **Клонирует репозиторий** — в `/opt/contour-app` (или обновляет, если уже есть).
5. **Генерирует `.env`** — с вашим значением `APP_PORT`.
6. **Настраивает Nginx** — подставляет порт в `nginx/default.conf`.
7. **Запускает стек** — `docker compose up -d --build`.
8. **Показывает результат** — URL для доступа к приложению.

✅ Контейнеры настроены с `restart: always` — после перезагрузки сервера приложение поднимется автоматически.

---

## 🔄 Обновление приложения

Чтобы получить последнюю версию из репозитория и пересобрать контейнеры:

```bash
sudo ./update.sh
```

Скрипт `update.sh`:
- Переходит в `/opt/contour-app`
- Выполняет `git pull --ff-only`
- Собирает и запускает обновлённые контейнеры: `docker compose build && docker compose up -d`
- Показывает статус: `docker compose ps`

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

1. Удалите контейнеры и тома:
   ```bash
   docker compose down -v
   ```

2. (Опционально) Отключите автообновление, если оно было настроено:
   ```bash
   sudo systemctl disable --now contour-update.timer || true
   sudo systemctl disable contour-update.service || true
   sudo rm -f /etc/systemd/system/contour-update.service /etc/systemd/system/contour-update.timer
   sudo systemctl daemon-reload
   ```

3. Удалите файлы приложения:
   ```bash
   sudo rm -rf /opt/contour-app
   ```

4. (Опционально) Если Docker больше не нужен — удалите его:
   ```bash
   sudo apt remove -y docker.io docker-compose docker-compose-plugin || true
   sudo docker system prune -a -f || true
   ```

---

> 💬 **Совет**: Все команды в этом руководстве можно копировать и вставлять — они проверены и работают «как есть».  
> 🐳 Приложение полностью контейнеризовано: минимум зависимостей на хосте, максимум предсказуемости.

*Документация актуальна для версии на базе Docker. При возникновении вопросов — проверяйте логи или создавайте issue в репозитории.* 🛠️

