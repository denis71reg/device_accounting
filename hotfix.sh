#!/bin/bash

set -e

echo "🔥 Применение хот-фикса..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Проверка наличия .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    exit 1
fi

# Получение обновлений (если используется git)
if [ -d .git ]; then
    echo "📥 Получение обновлений из git..."
    git pull || echo -e "${YELLOW}⚠️  Не удалось получить обновления из git${NC}"
fi

# Запуск тестов перед хот-фиксом (опционально, можно пропустить для экстренных случаев)
if [ "${SKIP_TESTS:-false}" != "true" ] && [ -f "run_tests.sh" ]; then
    echo "🧪 Запуск тестов перед хот-фиксом..."
    chmod +x run_tests.sh
    if ! ./run_tests.sh; then
        echo -e "${YELLOW}⚠️  Тесты не прошли. Для принудительного применения установите SKIP_TESTS=true${NC}"
        echo -e "${YELLOW}   Пример: SKIP_TESTS=true ./hotfix.sh${NC}"
        read -p "Продолжить без тестов? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Копирование обновленного кода в контейнер
echo "📦 Копирование обновленного кода..."
docker-compose -f docker-compose.prod.yml cp . app:/app/

# Перезапуск контейнера для применения изменений
echo "🔄 Перезапуск контейнера..."
docker-compose -f docker-compose.prod.yml restart app

# Ожидание запуска
echo "⏳ Ожидание запуска..."
sleep 3

# Применение миграций (если есть)
if [ -d migrations/versions ] && [ "$(ls -A migrations/versions/*.py 2>/dev/null)" ]; then
    echo "🗄️  Проверка миграций..."
    docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade 2>/dev/null || true
fi

# Проверка статуса
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Хот-фикс применен успешно!${NC}"
    echo ""
    echo "📋 Логи:"
    docker-compose -f docker-compose.prod.yml logs --tail=20 app
else
    echo -e "${RED}❌ Ошибка при применении хот-фикса. Проверьте логи:${NC}"
    docker-compose -f docker-compose.prod.yml logs app
    exit 1
fi


