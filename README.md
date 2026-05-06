# 🤖 Threads Bot Factory — SaaS Platform

Мультипользовательский SaaS бот для автоматизации Threads аккаунтов с веб-дашбордом.

## ✨ Возможности

- **Мульти-аккаунт** — управляй неограниченным кол-вом Threads аккаунтов
- **AI посты** — автоматическая генерация контента через OpenAI/Gemini
- **AI комментарии** — умные ответы на комментарии через ИИ
- **Веб-дашборд** — управление через браузер (FastAPI + Jinja2)
- **Telegram бот** — управление через Telegram
- **Расписание** — автоматический постинг по времени (APScheduler)
- **Мультипользователи** — каждый пользователь управляет своими аккаунтами

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка окружения
```bash
cp .env.example .env
# Заполни .env своими ключами
```

### 3. Запуск
```bash
python main.py
```

Открой браузер: `http://localhost:8000`

## ⚙️ Переменные окружения (.env)

| Переменная | Описание |
|-----------|----------|
| `BOT_TOKEN` | Telegram Bot Token (от @BotFather) |
| `OPENAI_API_KEY` | OpenAI API ключ для AI постов |
| `TELEGRAM_BOT_USERNAME` | Username бота (без @) |
| `SECRET_KEY` | Секретный ключ сессий |
| `DATABASE_URL` | URL базы данных (по умолчанию SQLite) |
| `ADMIN_IDS` | Telegram ID администраторов (через запятую) |

## 📁 Структура проекта

```
├── main.py              # Точка входа (webapp + bot)
├── webapp.py            # FastAPI веб-приложение
├── bot.py               # Telegram бот (aiogram)
├── database.py          # База данных (SQLAlchemy)
├── scheduler.py         # Планировщик постов
├── ai_engine.py         # AI движок
├── ai_handlers.py       # AI обработчики
├── ai_post_generator.py # Генерация постов
├── threads_api.py       # Threads API клиент
├── requirements.txt     # Зависимости
└── templates/           # HTML шаблоны дашборда
    ├── login.html
    └── dashboard.html
```

## 🌐 Деплой на Koyeb

См. [KOYEB.md](KOYEB.md)

## 🐳 Docker

```bash
docker build -t threads-bot-factory .
docker run -p 8000:8000 --env-file .env threads-bot-factory
```
