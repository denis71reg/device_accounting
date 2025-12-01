#!/bin/bash

set -e

echo "🚀 Запуск сервера Device Accounting..."
echo ""

cd "$(dirname "$0")"

# Проверка .env
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте его из env.example и настройте SECRET_KEY"
    exit 1
fi

# Остановка старых контейнеров
echo "🛑 Остановка старых контейнеров..."
docker-compose -f docker-compose.prod.yml down || true

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p instance logs
chmod 755 instance

# Сборка образа (если нужно)
echo "🔨 Проверка образа..."
docker-compose -f docker-compose.prod.yml build

# Запуск контейнеров
echo "▶️  Запуск контейнеров..."
docker-compose -f docker-compose.prod.yml up -d

# Ожидание запуска
echo "⏳ Ожидание запуска (10 секунд)..."
sleep 10

# Применение миграций
echo "🗄️  Применение миграций..."
docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade || echo "⚠️  Миграции уже применены"

# Проверка статуса
echo ""
echo "📊 Статус контейнеров:"
docker-compose -f docker-compose.prod.yml ps

# Проверка логов
echo ""
echo "📋 Последние логи (Ctrl+C для выхода):"
docker-compose -f docker-compose.prod.yml logs --tail=30 app

echo ""
echo "✅ Сервер должен быть доступен на:"
echo "   - Локально: http://127.0.0.1:5001"
echo "   - Через Nginx: http://127.0.0.1:2022"
echo ""
echo "Для просмотра логов в реальном времени:"
echo "   docker-compose -f docker-compose.prod.yml logs -f app"




