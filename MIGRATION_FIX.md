# Исправление миграции для разделения ФИО на три поля

## Проблема
Миграция `2cc3e299a376` не была идемпотентной и падала при повторном применении.

## Решение
Миграция обновлена и теперь:
- Проверяет существование колонок перед добавлением
- Корректно обрабатывает частично примененные миграции
- Безопасно удаляет старое поле `full_name`

## Применение на сервере

### Вариант 1: Автоматическое обновление (рекомендуется)
```bash
cd /opt/device_accounting
./update.sh
```

### Вариант 2: Ручное применение
```bash
cd /opt/device_accounting

# 1. Остановить контейнеры
docker-compose -f docker-compose.prod.yml down

# 2. Получить обновления (если используется git)
git pull

# 3. Пересобрать образ
docker-compose -f docker-compose.prod.yml build

# 4. Запустить контейнеры
docker-compose -f docker-compose.prod.yml up -d

# 5. Применить миграции
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# 6. Проверить статус
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs app
```

## Проверка
После применения миграции проверьте:
1. Статус контейнера: `docker-compose -f docker-compose.prod.yml ps`
2. Логи: `docker-compose -f docker-compose.prod.yml logs app`
3. Доступность приложения: `curl http://localhost:5001`

## Откат (если что-то пошло не так)
```bash
docker-compose -f docker-compose.prod.yml exec app flask db downgrade 5d35d8b8be66
```




