#!/bin/bash

# Скрипт для деплоя через Git
# Запускать на сервере в директории проекта

set -e

GIT_REPO="https://code.dev-ittest.ru/ittest/device-accounting/da-python.git"
# Резервный: https://github.com/denis71reg/device_accounting.git
PROJECT_DIR="/opt/device_accounting"  # Измените на вашу директорию
BRANCH="main"

echo "🚀 Деплой Device Accounting через Git"
echo "======================================"

# Проверка наличия git
if ! command -v git &> /dev/null; then
    echo "❌ Git не установлен. Установите: apt-get install git"
    exit 1
fi

# Создание директории проекта, если её нет
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📁 Создание директории проекта: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    echo "📥 Клонирование репозитория..."
    git clone "$GIT_REPO" .
else
    echo "📂 Переход в директорию проекта: $PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    echo "🔄 Обновление кода из Git..."
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
fi

echo "✅ Код обновлен из Git"

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаю из примера..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "✏️  ВАЖНО: Отредактируйте .env и установите SECRET_KEY"
        echo "   Сгенерировать ключ: python3 -c \"import secrets; print(secrets.token_hex(32))\""
        echo "   Затем запустите этот скрипт снова."
        exit 1
    else
        echo "❌ Файл env.example не найден!"
        exit 1
    fi
fi

# Создание необходимых директорий
echo "📁 Создание необходимых директорий..."
mkdir -p instance logs
chmod 755 instance

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и Docker Compose"
    exit 1
fi

# Остановка старых контейнеров (если есть)
echo "🛑 Остановка старых контейнеров..."
docker-compose -f docker-compose.prod.yml down || true

# Сборка образа
echo "🔨 Сборка Docker образа..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Запуск приложения
echo "▶️  Запуск приложения..."
docker-compose -f docker-compose.prod.yml up -d

# Ожидание запуска
echo "⏳ Ожидание запуска приложения..."
sleep 10

# Применение миграций
echo "🗄️  Применение миграций базы данных..."
docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade || echo "⚠️  Миграции уже применены или база данных не готова"

# Проверка статуса
echo "✅ Проверка статуса контейнеров..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Проверьте логи:"
echo "      docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "   2. Если нужно создать супер-администратора:"
echo "      docker-compose -f docker-compose.prod.yml exec app flask create-superadmin email@ittest-team.ru \"ФИО\" --password"
echo ""
echo "   3. Приложение должно быть доступно через Nginx на: https://da.dev-ittest.ru"
echo ""

