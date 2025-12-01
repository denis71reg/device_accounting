#!/bin/bash

# Скрипт для загрузки приложения на сервер
# Использование: ./upload_to_server.sh user@server-ip /path/on/server

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Проверка аргументов
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Использование: $0 user@server-ip /path/on/server${NC}"
    echo ""
    echo "Пример:"
    echo "  $0 root@192.168.1.100 /opt/device_accounting"
    exit 1
fi

SERVER=$1
REMOTE_PATH=$2

echo -e "${GREEN}🚀 Загрузка Device Accounting на сервер...${NC}"
echo "Сервер: $SERVER"
echo "Путь: $REMOTE_PATH"
echo ""

# Проверка SSH доступа
echo "🔐 Проверка SSH доступа..."
if ! ssh -o ConnectTimeout=5 "$SERVER" "echo 'SSH connection OK'" 2>/dev/null; then
    echo -e "${RED}❌ Не удалось подключиться к серверу!${NC}"
    echo "Проверьте:"
    echo "  - Доступность сервера"
    echo "  - SSH ключи настроены"
    echo "  - Правильность адреса и пользователя"
    exit 1
fi

echo -e "${GREEN}✅ SSH подключение установлено${NC}"

# Создание директории на сервере
echo "📁 Создание директории на сервере..."
ssh "$SERVER" "mkdir -p $REMOTE_PATH"

# Копирование файлов
echo "📦 Копирование файлов на сервер..."
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
    ./ "$SERVER:$REMOTE_PATH/"

echo -e "${GREEN}✅ Файлы скопированы${NC}"

# Настройка на сервере
echo "⚙️  Настройка на сервере..."
ssh "$SERVER" << EOF
    cd $REMOTE_PATH
    chmod +x setup_server.sh deploy.sh update.sh hotfix.sh 2>/dev/null || true
    
    # Проверка Docker
    if ! command -v docker &> /dev/null; then
        echo "${YELLOW}⚠️  Docker не установлен на сервере${NC}"
        echo "Установите Docker перед продолжением"
        exit 1
    fi
    
    # Создание .env если нет
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            echo "${YELLOW}⚠️  Создан файл .env из примера${NC}"
            echo "${YELLOW}⚠️  ВАЖНО: Отредактируйте .env и установите SECRET_KEY!${NC}"
        fi
    fi
    
    echo "${GREEN}✅ Настройка завершена${NC}"
EOF

echo ""
echo -e "${GREEN}✅ Загрузка завершена!${NC}"
echo ""
echo "Следующие шаги на сервере:"
echo "  1. Подключитесь: ssh $SERVER"
echo "  2. Перейдите: cd $REMOTE_PATH"
echo "  3. Отредактируйте .env: nano .env"
echo "  4. Запустите: ./deploy.sh"
echo ""
echo "Или выполните все одной командой:"
echo "  ssh $SERVER 'cd $REMOTE_PATH && ./setup_server.sh && ./deploy.sh'"
echo ""





