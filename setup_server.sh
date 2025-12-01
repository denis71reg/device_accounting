#!/bin/bash

set -e

echo "🚀 Настройка сервера для Device Accounting..."

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен!${NC}"
    echo "Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose не установлен!${NC}"
    echo "Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker и Docker Compose установлены${NC}"

# Создание директорий
echo "📁 Создание необходимых директорий..."
mkdir -p instance logs
chmod 755 instance

# Проверка .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Файл .env не найден. Создаю из примера...${NC}"
    if [ -f env.example ]; then
        cp env.example .env
        echo -e "${GREEN}✅ Файл .env создан${NC}"
        echo -e "${YELLOW}⚠️  ВАЖНО: Отредактируйте .env и установите SECRET_KEY!${NC}"
        echo "   Сгенерировать ключ: python -c \"import secrets; print(secrets.token_hex(32))\""
    else
        echo -e "${RED}❌ Файл env.example не найден!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Файл .env найден${NC}"
fi

# Проверка SECRET_KEY
if grep -q "your-secret-key-here" .env 2>/dev/null || grep -q "dev-secret" .env 2>/dev/null; then
    echo -e "${RED}❌ ВАЖНО: Измените SECRET_KEY в файле .env!${NC}"
    echo "   Текущий ключ небезопасен для продакшена"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Сервер готов (Docker установлен).${NC}"
echo ""
echo "Если команды docker требуют sudo, добавьте пользователя в группу docker:"
echo "  sudo usermod -aG docker \$USER && newgrp docker"
echo ""
echo "Следующие шаги:"
echo "  1. Убедитесь, что SECRET_KEY в .env изменен"
echo "  2. Запустите: ./deploy.sh"
echo ""


