#!/bin/bash
# Быстрое обновление на сервере - выполните НА СЕРВЕРЕ

cd /opt/device_accounting

echo "🔄 Быстрое обновление..."

# Остановка
docker-compose -f docker-compose.prod.yml down

# Пересборка БЕЗ кэша (важно!)
docker-compose -f docker-compose.prod.yml build --no-cache

# Запуск
docker-compose -f docker-compose.prod.yml up -d

# Ждем
sleep 5

# Миграции
docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade

echo "✅ Обновление завершено!"
echo "Проверьте: https://da.dev-ittest.ru"
echo "Должно быть: 'Девайсы' вместо 'Инвентарь', нет кнопок 'Выдать' и 'Вернуть'"




