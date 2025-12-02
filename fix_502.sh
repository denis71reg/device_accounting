#!/bin/bash
# Скрипт для исправления ошибки 502 Bad Gateway

set -e

echo "🔍 Диагностика проблемы 502 Bad Gateway..."
echo ""

cd "$(dirname "$0")" || exit 1

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки статуса
check_status() {
    echo -e "${YELLOW}📊 Проверка статуса контейнеров...${NC}"
    docker-compose -f docker-compose.prod.yml ps
    echo ""
}

# Функция для проверки логов
check_logs() {
    echo -e "${YELLOW}📋 Последние логи приложения:${NC}"
    docker-compose -f docker-compose.prod.yml logs app --tail=30 || echo "Контейнер не запущен"
    echo ""
}

# Функция для проверки порта
check_port() {
    echo -e "${YELLOW}🔌 Проверка порта 5001:${NC}"
    if command -v ss >/dev/null 2>&1; then
        sudo ss -tlnp | grep 5001 || echo "Порт 5001 не слушается"
    elif command -v netstat >/dev/null 2>&1; then
        sudo netstat -tlnp | grep 5001 || echo "Порт 5001 не слушается"
    else
        echo "Не удалось проверить порт (установите ss или netstat)"
    fi
    echo ""
}

# Функция для проверки nginx
check_nginx() {
    echo -e "${YELLOW}🌐 Проверка nginx:${NC}"
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✅ Nginx запущен${NC}"
    else
        echo -e "${RED}❌ Nginx не запущен${NC}"
    fi
    
    if [ -f /var/log/nginx/da_error.log ]; then
        echo "Последние ошибки nginx:"
        tail -20 /var/log/nginx/da_error.log
    fi
    echo ""
}

# Шаг 1: Диагностика
echo "=== ШАГ 1: ДИАГНОСТИКА ==="
check_status
check_logs
check_port
check_nginx

# Шаг 2: Проверка .env
echo "=== ШАГ 2: ПРОВЕРКА КОНФИГУРАЦИИ ==="
if [ ! -f .env ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    if [ -f env.example ]; then
        echo "Создаю .env из env.example..."
        cp env.example .env
        echo -e "${YELLOW}⚠️  Отредактируйте .env и установите SECRET_KEY${NC}"
        echo "   Сгенерировать ключ: python3 -c \"import secrets; print(secrets.token_hex(32))\""
        exit 1
    else
        echo -e "${RED}❌ Файл env.example не найден!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Файл .env найден${NC}"
    if grep -q "SECRET_KEY=" .env && ! grep -q "SECRET_KEY=$" .env; then
        echo -e "${GREEN}✅ SECRET_KEY установлен${NC}"
    else
        echo -e "${RED}❌ SECRET_KEY не установлен в .env!${NC}"
        exit 1
    fi
fi
echo ""

# Шаг 3: Остановка старых контейнеров
echo "=== ШАГ 3: ОСТАНОВКА СТАРЫХ КОНТЕЙНЕРОВ ==="
docker-compose -f docker-compose.prod.yml down || true
echo ""

# Шаг 4: Создание директорий
echo "=== ШАГ 4: СОЗДАНИЕ ДИРЕКТОРИЙ ==="
mkdir -p instance logs
chmod 755 instance logs
echo -e "${GREEN}✅ Директории созданы${NC}"
echo ""

# Шаг 5: Пересборка и запуск
echo "=== ШАГ 5: ПЕРЕСБОРКА И ЗАПУСК ==="
echo "Пересборка образа..."
docker-compose -f docker-compose.prod.yml build --no-cache

echo "Запуск контейнеров..."
docker-compose -f docker-compose.prod.yml up -d

echo "Ожидание запуска (15 секунд)..."
sleep 15
echo ""

# Шаг 6: Применение миграций
echo "=== ШАГ 6: ПРИМЕНЕНИЕ МИГРАЦИЙ ==="
docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade || echo "⚠️  Миграции уже применены или база данных не готова"
echo ""

# Шаг 7: Проверка после запуска
echo "=== ШАГ 7: ПРОВЕРКА ПОСЛЕ ЗАПУСКА ==="
check_status
check_logs
check_port

# Проверка доступности приложения
echo -e "${YELLOW}🌐 Проверка доступности приложения:${NC}"
if curl -f -s http://127.0.0.1:5001 > /dev/null; then
    echo -e "${GREEN}✅ Приложение доступно на http://127.0.0.1:5001${NC}"
else
    echo -e "${RED}❌ Приложение недоступно на http://127.0.0.1:5001${NC}"
    echo "Проверьте логи выше для диагностики"
fi
echo ""

# Проверка nginx
echo -e "${YELLOW}🔄 Перезагрузка nginx:${NC}"
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl reload nginx || sudo systemctl restart nginx
    echo -e "${GREEN}✅ Nginx перезагружен${NC}"
else
    echo "⚠️  Не удалось перезагрузить nginx (установите systemctl)"
fi
echo ""

# Финальная проверка
echo "=== ФИНАЛЬНАЯ ПРОВЕРКА ==="
echo "Проверьте доступность сайта:"
echo "  - Локально: http://127.0.0.1:5001"
echo "  - Через nginx: http://127.0.0.1:2022"
echo "  - Внешний доступ: https://da.dev-ittest.ru"
echo ""
echo "Для просмотра логов в реальном времени:"
echo "  docker-compose -f docker-compose.prod.yml logs -f app"
echo ""




