# Backend CI/CD Pipeline

Этот документ описывает CI/CD pipeline для backend проекта parking monitoring.

## Обзор

CI/CD pipeline настроен на GitHub Actions и включает:

1. **Linting stage** - проверка качества кода
2. **Test stage** - интеграционные тесты с PostgreSQL service

## Структура Pipeline

### Stage 1: Linting

Три параллельные задачи для проверки кода:

- `lint:flake8` - проверка стиля кода и поиск ошибок
- `lint:mypy` - статическая типизация (с allow_failure)
- `lint:format` - проверка форматирования кода (black)

### Stage 2: Integration Tests

- `test` - запуск всех тестов с PostgreSQL service
  - Запускает PostgreSQL как GitHub Actions service
  - Устанавливает только тестовые зависимости (без heavy packages)
  - Выполняет pytest с покрытием кода
  - Генерирует coverage отчет в XML формате
  - Загружает coverage на Codecov (опционально)

**Примечание:** В CI используется `requirements-test.txt` который не включает тяжелые зависимости (torch, opencv, ultralytics) для экономии места и времени.

## Локальный запуск тестов

### Способ 1: С Docker Compose (рекомендуется)

```bash
# Запуск тестов в Docker
cd backend
docker-compose -f docker-compose.test.yml up --build

# После завершения тестов очистка
docker-compose -f docker-compose.test.yml down -v
```

### Способ 2: Локально (требует PostgreSQL)

```bash
# Убедись что PostgreSQL запущен на localhost:5432
# Или установи переменную окружения
export DB_HOST=localhost

# Установка зависимостей (для CI используй requirements-test.txt)
pip install -r requirements-test.txt

# Запуск тестов
pytest tests/ -v --cov=app --cov-report=term

# Запуск конкретного тестового файла
pytest tests/test_cameras.py -v

# Запуск с подробным выводом
pytest tests/ -vv -s
```

## Покрытие тестов

Тесты покрывают следующие CRUD endpoints:

### ✅ Cameras (`test_cameras.py`)
- Создание камеры
- Получение списка камер
- Получение конкретной камеры
- Обновление камеры
- Удаление камеры

### ✅ Parking Lots (`test_parking_lots.py`)
- Создание parking lot
- Получение списка parking lots
- Получение конкретного parking lot
- Обновление parking lot
- Удаление parking lot
- Валидация несуществующей камеры

### ✅ Parking Slots (`test_parking_slots.py`)
- Создание parking slot
- Получение списка parking slots
- Получение конкретного parking slot
- Обновление parking slot
- Удаление parking slot
- Валидация несуществующей камеры

### ✅ Detections (`test_detections.py`)
- Создание detection
- Получение списка detections
- Получение конкретной detection
- Получение detections по video_id
- Удаление detection
- Валидация несуществующего видео

### ✅ Occupancy Events (`test_events.py`)
- Создание occupancy event
- Получение списка occupancy events
- Получение конкретного occupancy event
- Получение events по parking_lot_id
- Удаление occupancy event
- Валидация неверного статуса

### ✅ Videos (`test_videos.py`)
- Получение списка видео
- Получение конкретного видео
- Обновление видео
- Удаление видео
- Получение видео по camera_id
- Получение статистики видео
- Валидация несуществующего видео

## CI/CD Workflow

```mermaid
graph LR
    A[Push to GitHub] --> B{Lint Stage}
    B --> C[flake8]
    B --> D[mypy]
    B --> E[black --check]
    C & D & E --> F{All Pass?}
    F -->|Yes| G[Test Stage]
    F -->|No| H[Failed]
  G --> I[Start PostgreSQL Service]
  I --> J[Run pytest]
  J --> K[Generate Coverage]
  K --> L[Upload to Codecov]
  L --> M[Success]
```

## Переменные окружения CI

В GitHub Actions автоматически устанавливаются следующие переменные:

- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_DB=parking_monitoring_test`
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/parking_monitoring_test`
- `SYNC_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/parking_monitoring_test`
- `DB_HOST=localhost`

## Просмотр результатов в GitLab

1. Открой свой проект на GitHub
2. Перейди в раздел **Actions** → **Workflows**
3. Выбери нужный workflow для просмотра деталей
4. Ты увидишь:
   - Статус каждого job (lint/test)
   - Логи выполнения
   - Coverage отчет
   - Артефакты (coverage.xml)

## Устранение неполадок

### Тесты падают в CI но работают локально

Проверь:
1. Используется ли `DB_HOST=localhost` (в GitHub Actions)
2. Все ли зависимости установлены в requirements.txt
3. Все ли переменные окружения установлены в workflow

### Flake8 ошибки

```bash
# Автоисправление некоторых проблем
pip install black isort
black app tests/
isort app tests/

# Просмотр детальной информации
flake8 app tests --show-source
```

### MyPy ошибки

Mypy настроен с `allow_failure: true`, но если хочешь исправить:

```bash
# Запуск mypy локально
mypy app --ignore-missing-imports

# Добавь type hints в проблемные места
```

### Docker Compose проблемы

```bash
# Проверка статуса контейнеров
docker-compose -f docker-compose.test.yml ps

# Просмотр логов
docker-compose -f docker-compose.test.yml logs

# Полная очистка
docker-compose -f docker-compose.test.yml down -v --remove-orphans
```

## Добавление новых тестов

1. Создай файл в `backend/tests/` с префиксом `test_`
2. Используй async fixtures из `conftest.py`:
   - `async_client` - для HTTP запросов
   - `db_session` - для работы с базой данных
3. Следуй паттерну существующих тестов
4. Покрывай основные сценарии: create, read, update, delete

Пример:

```python
"""Tests for new endpoint."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import YourModel

@pytest.mark.asyncio
async def test_create_your_model(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating a new model instance."""
    response = await async_client.post(
        "/api/v1/your-endpoint/",
        json={"field": "value"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == "value"
```

## Best Practices

1. **Изолированные тесты**: Каждый тест должен быть независимым
2. **Очистка данных**: Используй fixtures для автоматической очистки
3. **Покрытие**: Стремись к 80%+ покрытия кода тестами
4. **Читаемость**: Используй описательные названия тестов
5. **Ассерты**: Проверяй статус коды и важные поля в ответе

## Дополнительные ресурсы

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Flake8 Style Guide](https://flake8.pycqa.org/)
- [Codecov Documentation](https://docs.codecov.com/)
