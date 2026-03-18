# 🔁 Polymarket Copy Trader Bot

Бот для автоматического копирования ордеров другого аккаунта на платформе [Polymarket](https://polymarket.com) с веб-интерфейсом управления.

## Возможности

- 🔍 **Отслеживание** — периодический опрос ордеров целевого кошелька через Polymarket CLOB API
- 📋 **Копирование** — автоматическое создание зеркальных ордеров с настраиваемым множителем размера
- 🖥️ **Веб-интерфейс** — запуск/остановка бота, настройка параметров, просмотр истории ордеров
- 🛡️ **Идемпотентность** — каждый ордер копируется только один раз
- 🐳 **Docker** — деплой одной командой

## Структура проекта

```
POLY1/
├── backend/
│   ├── __init__.py
│   ├── config.py          # Загрузка конфигурации из .env
│   ├── models.py          # Pydantic модели
│   ├── polymarket_client.py  # Обёртка над py-clob-client
│   ├── tracker.py         # Трекер ордеров с APScheduler
│   ├── main.py            # FastAPI приложение
│   └── requirements.txt
├── frontend/
│   ├── index.html         # Веб-панель управления
│   ├── style.css          # Тёмная тема
│   └── app.js             # Клиентская логика
├── .env.example           # Шаблон конфигурации
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Установка и запуск

### Вариант 1: Docker (рекомендуется)

1. Скопируйте `.env.example` в `.env` и заполните переменные:
   ```bash
   cp .env.example .env
   ```

2. Запустите через Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Откройте браузер: [http://localhost:8000](http://localhost:8000)

### Вариант 2: Локальный запуск

1. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate  # или venv\Scripts\activate на Windows
   pip install -r backend/requirements.txt
   ```

2. Создайте `.env` файл:
   ```bash
   cp .env.example .env
   # Отредактируйте .env и вставьте свои API ключи
   ```

3. Запустите сервер:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

4. Откройте браузер: [http://localhost:8000](http://localhost:8000)

## Конфигурация

| Переменная | Описание | По умолчанию |
|---|---|---|
| `POLYMARKET_API_KEY` | API ключ Polymarket | — |
| `POLYMARKET_API_SECRET` | API секрет Polymarket | — |
| `POLYMARKET_PASSPHRASE` | Пароль API | — |
| `CLOB_API_URL` | URL CLOB API | `https://clob.polymarket.com` |
| `CHAIN_ID` | ID сети Polygon | `137` |
| `TARGET_WALLET_ADDRESS` | Адрес отслеживаемого кошелька | — |
| `PRIVATE_KEY` | Приватный ключ вашего кошелька | — |
| `COPY_MULTIPLIER` | Множитель размера ордера | `1.0` |
| `POLL_INTERVAL_SECONDS` | Интервал опроса (секунды) | `10` |
| `HOST` | Хост сервера | `0.0.0.0` |
| `PORT` | Порт сервера | `8000` |

## API Endpoints

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/api/status` | Статус бота |
| `POST` | `/api/start` | Запустить бота |
| `POST` | `/api/stop` | Остановить бота |
| `GET` | `/api/orders/target` | Ордера целевого кошелька |
| `GET` | `/api/orders/copied` | История скопированных ордеров |
| `GET` | `/api/orders/own` | Открытые ордера бота |
| `POST` | `/api/config` | Обновить конфигурацию |
| `POST` | `/api/cancel-all` | Отменить все открытые ордера |
| `GET` | `/api/markets` | Список доступных рынков |

## ⚠️ Предупреждение о рисках

> **Используйте на свой страх и риск.** Торговля на рынках предсказаний сопряжена с финансовыми рисками. Автор не несёт ответственности за убытки, возникшие в результате использования данного программного обеспечения. Никогда не используйте средства, потерю которых вы не можете себе позволить.

- Убедитесь, что ваш API ключ имеет только необходимые права
- Никогда не публикуйте приватный ключ и `.env` файл
- Протестируйте на тестовой сети перед реальным использованием (`CHAIN_ID=80002`)
