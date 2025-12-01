# Отладка проблемы запуска сервера

## Шаги для диагностики на сервере

### 1. Проверить логи контейнера
```bash
cd /opt/device_accounting
docker-compose -f docker-compose.prod.yml logs app --tail=100
```

### 2. Проверить статус контейнера
```bash
docker-compose -f docker-compose.prod.yml ps
```

### 3. Попробовать запустить вручную
```bash
docker-compose -f docker-compose.prod.yml exec app python -c "from da import create_app; app = create_app(); print('OK')"
```

### 4. Проверить миграции
```bash
docker-compose -f docker-compose.prod.yml exec app flask db current
docker-compose -f docker-compose.prod.yml exec app flask db history
```

### 5. Попробовать применить миграции вручную
```bash
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### 6. Проверить структуру базы данных
```bash
docker-compose -f docker-compose.prod.yml exec app python -c "
from da import create_app
from da.extensions import db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('employees')]
    print('Колонки employees:', columns)
"
```

### 7. Если контейнер не запускается, пересобрать
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f app
```

### 8. Проверить переменные окружения
```bash
docker-compose -f docker-compose.prod.yml exec app env | grep -E "FLASK|DATABASE|SECRET"
```

## Возможные проблемы и решения

### Проблема: Ошибка миграции
**Решение:** Применить миграцию вручную с проверкой:
```bash
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### Проблема: Контейнер падает сразу после запуска
**Решение:** Проверить логи и пересобрать образ:
```bash
docker-compose -f docker-compose.prod.yml logs app
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Проблема: База данных заблокирована
**Решение:** Остановить все контейнеры и перезапустить:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Проблема: Ошибка импорта
**Решение:** Проверить, что все файлы скопированы:
```bash
docker-compose -f docker-compose.prod.yml exec app ls -la /app/da/models.py
docker-compose -f docker-compose.prod.yml exec app ls -la /app/migrations/versions/
```




