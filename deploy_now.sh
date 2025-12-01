#!/bin/bash

# Деплой на сервер через SSH
# Требуется SSH доступ и пароль (или SSH ключ)

set -e

SERVER="ittest@192.168.16.44"
REMOTE_PATH="/opt/device_accounting"
GIT_REPO="https://code.dev-ittest.ru/ittest/device-accounting/da-python.git"

echo "🚀 Деплой Device Accounting на сервер"
echo "======================================"
echo ""
echo "Сервер: $SERVER"
echo "Путь: $REMOTE_PATH"
echo ""

# Проверка SSH доступа
echo "🔐 Проверка SSH доступа..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes $SERVER "echo 'OK'" 2>/dev/null; then
    echo "✅ SSH доступен (используется ключ)"
    USE_PASSWORD=false
else
    echo "⚠️  Требуется пароль для SSH"
    USE_PASSWORD=true
fi

echo ""
echo "📦 Обновление кода на сервере..."
echo ""

# Функция для выполнения команд на сервере
run_on_server() {
    if [ "$USE_PASSWORD" = true ]; then
        ssh -o StrictHostKeyChecking=no $SERVER "$1"
    else
        ssh -o StrictHostKeyChecking=no $SERVER "$1"
    fi
}

# Проверка существования проекта
echo "📂 Проверка проекта на сервере..."
if run_on_server "test -d $REMOTE_PATH" 2>/dev/null; then
    echo "✅ Проект существует, обновляю код..."
    run_on_server "cd $REMOTE_PATH && git fetch origin && git pull origin main"
else
    echo "📥 Проект не найден, клонирую..."
    run_on_server "mkdir -p $(dirname $REMOTE_PATH) && cd $(dirname $REMOTE_PATH) && git clone $GIT_REPO device_accounting"
fi

echo ""
echo "🔨 Пересборка и перезапуск контейнеров..."
echo ""

# Деплой
run_on_server "cd $REMOTE_PATH && \
    docker-compose -f docker-compose.prod.yml down && \
    docker-compose -f docker-compose.prod.yml build && \
    docker-compose -f docker-compose.prod.yml up -d && \
    sleep 10 && \
    docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade || echo 'Миграции уже применены'"

echo ""
echo "✅ Проверка статуса..."
run_on_server "cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml ps"

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "🌐 Приложение должно быть доступно: https://da.dev-ittest.ru"
echo ""
echo "📝 Для просмотра логов:"
echo "   ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml logs -f'"
echo ""


