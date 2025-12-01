#!/bin/bash

set -e

echo "🔧 Настройка Nginx для Device Accounting..."

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Этот скрипт должен быть запущен от root (используйте sudo)"
    exit 1
fi

# Проверка установки Nginx
if ! command -v nginx &> /dev/null; then
    echo "📦 Установка Nginx..."
    apt-get update
    apt-get install -y nginx
fi

# Создание конфигурации
CONFIG_FILE="/etc/nginx/sites-available/device_accounting"
echo "📝 Создание конфигурации Nginx..."

cat > "$CONFIG_FILE" << 'EOF'
# Конфигурация Nginx для Device Accounting
# Проксирование на порт 2022

server {
    listen 2022;
    server_name 91.193.239.177;

    # Логи
    access_log /var/log/nginx/da_access.log;
    error_log /var/log/nginx/da_error.log;

    # Максимальный размер загружаемых файлов
    client_max_body_size 10M;

    # Проксирование на приложение
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Таймауты
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Статические файлы (если будут добавлены)
    location /static {
        alias /opt/device_accounting/da/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Активация конфигурации
if [ -f "/etc/nginx/sites-enabled/device_accounting" ]; then
    rm /etc/nginx/sites-enabled/device_accounting
fi
ln -sf "$CONFIG_FILE" /etc/nginx/sites-enabled/device_accounting

# Удаление дефолтной конфигурации (если нужно)
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    echo "⚠️  Удаление дефолтной конфигурации Nginx..."
    rm /etc/nginx/sites-enabled/default
fi

# Проверка конфигурации
echo "🔍 Проверка конфигурации Nginx..."
if nginx -t; then
    echo "✅ Конфигурация Nginx корректна"
else
    echo "❌ Ошибка в конфигурации Nginx!"
    exit 1
fi

# Перезапуск Nginx
echo "🔄 Перезапуск Nginx..."
systemctl restart nginx
systemctl enable nginx

# Проверка статуса
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx успешно запущен"
else
    echo "❌ Ошибка запуска Nginx!"
    exit 1
fi

# Проверка порта
echo "🔍 Проверка порта 2022..."
if netstat -tuln | grep -q ":2022"; then
    echo "✅ Порт 2022 слушается"
else
    echo "⚠️  Порт 2022 не слушается. Проверьте firewall:"
    echo "   sudo ufw allow 2022/tcp"
fi

echo ""
echo "✅ Настройка Nginx завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Убедитесь, что порт 2022 открыт в firewall:"
echo "      sudo ufw allow 2022/tcp"
echo ""
echo "   2. Приложение будет доступно по адресу:"
echo "      http://91.193.239.177:2022"
echo ""
echo "   3. Проверьте логи Nginx:"
echo "      sudo tail -f /var/log/nginx/da_access.log"
echo "      sudo tail -f /var/log/nginx/da_error.log"




