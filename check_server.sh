#!/bin/bash

echo "🔍 Проверка статуса сервера Device Accounting..."
echo ""

# Проверка Docker
echo "1. Проверка Docker:"
if command -v docker &> /dev/null; then
    docker --version
else
    echo "❌ Docker не установлен!"
    exit 1
fi

# Проверка контейнеров
echo ""
echo "2. Статус контейнеров:"
if [ -f docker-compose.prod.yml ]; then
    docker-compose -f docker-compose.prod.yml ps
else
    echo "❌ Файл docker-compose.prod.yml не найден!"
    exit 1
fi

# Проверка портов
echo ""
echo "3. Проверка портов:"
if command -v ss &> /dev/null; then
    echo "Порт 5001 (приложение):"
    sudo ss -tlnp | grep 5001 || echo "   ❌ Порт 5001 не слушается"
    echo "Порт 2022 (nginx):"
    sudo ss -tlnp | grep 2022 || echo "   ❌ Порт 2022 не слушается"
elif command -v netstat &> /dev/null; then
    echo "Порт 5001 (приложение):"
    sudo netstat -tlnp | grep 5001 || echo "   ❌ Порт 5001 не слушается"
    echo "Порт 2022 (nginx):"
    sudo netstat -tlnp | grep 2022 || echo "   ❌ Порт 2022 не слушается"
else
    echo "⚠️  ss или netstat не найдены, пропускаю проверку портов"
fi

# Проверка логов
echo ""
echo "4. Последние логи приложения:"
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    docker-compose -f docker-compose.prod.yml logs app --tail=20
else
    echo "❌ Контейнер не запущен!"
fi

# Проверка nginx
echo ""
echo "5. Статус Nginx:"
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx запущен"
    sudo systemctl status nginx --no-pager -l | head -10
else
    echo "❌ Nginx не запущен"
fi

# Проверка доступности
echo ""
echo "6. Проверка доступности:"
echo "Локально (127.0.0.1:5001):"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:5001 || echo "   ❌ Недоступно"

echo "Через Nginx (127.0.0.1:2022):"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:2022 || echo "   ❌ Недоступно"

echo ""
echo "✅ Проверка завершена"




