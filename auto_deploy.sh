#!/bin/bash
# Автоматический деплой на сервер
# Использование: ./auto_deploy.sh

set -e

SERVER="ittest@192.168.16.44"
REMOTE_PATH="/opt/device_accounting"

echo "🚀 Автоматический деплой Device Accounting..."
echo "Сервер: $SERVER"
echo "Путь: $REMOTE_PATH"
echo ""

# Проверка SSH доступа
echo "🔐 Проверка SSH доступа..."
if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SERVER" "echo 'SSH OK'" 2>/dev/null; then
    echo "❌ Не удалось подключиться к серверу!"
    echo ""
    echo "Возможные причины:"
    echo "  1. Сервер недоступен (192.168.16.44)"
    echo "  2. Требуется VPN подключение"
    echo "  3. SSH ключ не настроен"
    echo ""
    echo "Альтернативный способ:"
    echo "  1. Загрузите deploy_package.tar.gz на сервер вручную"
    echo "  2. На сервере выполните:"
    echo "     cd $REMOTE_PATH"
    echo "     tar -xzf deploy_package.tar.gz"
    echo "     ./deploy_remote.sh"
    exit 1
fi

echo "✅ SSH подключение установлено"
echo ""

# Загрузка файлов
echo "📦 Загрузка файлов на сервер..."
rsync -avz --progress \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'instance' \
    --exclude '.env' \
    --exclude '*.db' \
    --exclude '*.log' \
    --exclude '.DS_Store' \
    --exclude 'deploy_package.tar.gz' \
    ./ "$SERVER:$REMOTE_PATH/"

echo "✅ Файлы загружены"
echo ""

# Выполнение деплоя на сервере
echo "🚀 Запуск деплоя на сервере..."
ssh "$SERVER" << 'ENDSSH'
    cd /opt/device_accounting
    
    # Проверка .env
    if [ ! -f .env ]; then
        echo "⚠️  Файл .env не найден. Создаю из примера..."
        if [ -f env.example ]; then
            cp env.example .env
            echo "✏️  ВАЖНО: Отредактируйте .env и установите SECRET_KEY!"
            exit 1
        fi
    fi
    
    # Создание директорий
    mkdir -p instance logs
    chmod 755 instance
    
    # Остановка старых контейнеров
    echo "🛑 Остановка старых контейнеров..."
    docker-compose -f docker-compose.prod.yml down || true
    
    # Сборка образа
    echo "🔨 Сборка Docker образа..."
    docker-compose -f docker-compose.prod.yml build
    
    # Запуск приложения
    echo "▶️  Запуск приложения..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Ожидание запуска
    echo "⏳ Ожидание запуска приложения..."
    sleep 5
    
    # Применение миграций
    echo "🗄️  Применение миграций базы данных..."
    docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade || echo "⚠️  Миграции уже применены"
    
    # Проверка статуса
    echo "✅ Проверка статуса..."
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "✅ Деплой завершен!"
    echo "📝 Приложение доступно на: https://da.dev-ittest.ru"
ENDSSH

echo ""
echo "✅ Автоматический деплой завершен успешно!"




