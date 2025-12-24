 # Parking Monitoring System - Backend

Backend сервис для системы мониторинга парковочных мест на основе компьютерного зрения.

## Технологический стек

- **FastAPI** - веб-фреймворк
- **SQLAlchemy 2.0** - ORM для работы с БД
- **PostgreSQL** - реляционная база данных
- **TaskIQ** - очередь задач для асинхронной обработки
- **Ultralytics YOLO** - детекция транспортных средств
- **Alembic** - миграции БД

## Установка

### 1. Создайте виртуальное окружение

```bash
python3.11 -m venv venv
source venv/bin/activate  # На macOS/Linux
# или
venv\Scripts\activate  # На Windows
```

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Настройте окружение

Скопируйте `.env.example` в `.env` и отредактируйте параметры:

```bash
cp .env.example .env
```

### 4. Запустите PostgreSQL

```bash
# Используя Docker
docker run -d \
  --name parking-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=parking_monitoring \
  -p 5432:5432 \
  postgres:15
```

### 5. Создайте миграции и примените их

```bash
# Создать первую миграцию
alembic revision --autogenerate -m "Initial migration"

# Применить миграции
alembic upgrade head
```

### 6. Создайте директории для данных

```bash
mkdir -p data/videos data/frames models
```

### 7. Скачайте YOLO модель

```bash
# Модель будет скачана автоматически при первом запуске
# Или скачайте вручную и поместите в models/
```

## Запуск

### Запуск API сервера

```bash
python run.py
```

Или используя uvicorn напрямую:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен по адресу: http://localhost:8000

Документация API: http://localhost:8000/docs

### Запуск TaskIQ воркера

используя taskiq напрямую:

```bash
taskiq worker app.tasks.video_tasks:broker
```

## Структура проекта

```
backend/
├── alembic/              # Миграции БД
│   ├── versions/
│   └── env.py
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/
│   │       └── endpoints/
│   ├── db/               # База данных
│   │   └── models/
│   ├── schemas/          # Pydantic схемы
│   ├── tasks/            # TaskIQ задачи
│   ├── config.py         # Конфигурация
│   └── main.py           # FastAPI приложение
├── data/                 # Данные (не в git)
│   ├── videos/
│   └── frames/
├── models/               # YOLO модели (не в git)
├── tests/                # Тесты
├── alembic.ini
├── requirements.txt
├── run.py               # Запуск API
└── worker.py            # Запуск воркера
```

## API Endpoints

### Cameras

- `POST /api/v1/cameras` - Создать камеру
- `GET /api/v1/cameras` - Список камер
- `GET /api/v1/cameras/{id}` - Получить камеру
- `PATCH /api/v1/cameras/{id}` - Обновить камеру
- `DELETE /api/v1/cameras/{id}` - Удалить камеру

### Parking Lots

- `POST /api/v1/parking-lots` - Создать парковочную зону
- `GET /api/v1/parking-lots` - Список зон
- `GET /api/v1/parking-lots/{id}` - Получить зону
- `PATCH /api/v1/parking-lots/{id}` - Обновить зону
- `DELETE /api/v1/parking-lots/{id}` - Удалить зону

### Parking Slots

- `POST /api/v1/parking-slots` - Создать парковочное место
- `GET /api/v1/parking-slots` - Список мест
- `GET /api/v1/parking-slots/{id}` - Получить место
- `PATCH /api/v1/parking-slots/{id}` - Обновить место
- `DELETE /api/v1/parking-slots/{id}` - Удалить место

### Videos

- `POST /api/v1/videos/upload` - Загрузить видео
- `GET /api/v1/videos` - Список видео
- `GET /api/v1/videos/{id}` - Получить видео
- `GET /api/v1/videos/{id}/status` - Статус обработки
- `DELETE /api/v1/videos/{id}` - Удалить видео

### Events

- `GET /api/v1/events` - Список событий занятости
- `GET /api/v1/events/{id}` - Получить событие
- `GET /api/v1/events/stats/current` - Текущая статистика

## Разработка

### Форматирование кода

```bash
black app/
```

### Линтинг

```bash
flake8 app/
```

### Запуск тестов

```bash
pytest
```

## Работа с базой данных

### Создание новой миграции

```bash
alembic revision --autogenerate -m "Description"
```

### Применение миграций

```bash
alembic upgrade head
```

### Откат миграции

```bash
alembic downgrade -1
```

### Просмотр истории

```bash
alembic history
```

## Обработка видео

После загрузки видео через `/api/v1/videos/upload`, система автоматически:

1. Сохраняет видео в `data/videos/`
2. Создает запись в БД
3. Отправляет задачу в очередь TaskIQ
4. Воркер обрабатывает видео кадр за кадром
5. Детектирует транспортные средства с помощью YOLO
6. Определяет занятость парковочных мест
7. Сохраняет события в БД

## Мониторинг

### Проверка здоровья API

```bash
curl http://localhost:8000/health
```

### Проверка статуса обработки видео

```bash
curl http://localhost:8000/api/v1/videos/{video_id}/status
```

