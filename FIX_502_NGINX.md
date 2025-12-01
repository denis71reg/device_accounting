# Исправление ошибки 502 Bad Gateway

## Проблема
Nginx возвращает 502 Bad Gateway, хотя приложение работает на `localhost:5001`.

## Диагностика
✅ Контейнер работает: `Up (healthy)`  
✅ Приложение отвечает: `HTTP 302` на `http://localhost:5001`  
❌ Nginx не может подключиться к приложению

## Решение

### 1. Проверьте текущую конфигурацию nginx

```bash
sudo cat /etc/nginx/sites-enabled/da.dev-ittest.ru
# или
sudo cat /etc/nginx/conf.d/da.dev-ittest.ru.conf
```

### 2. Создайте/обновите конфигурацию nginx

```bash
sudo tee /etc/nginx/sites-available/da.dev-ittest.ru > /dev/null << 'EOF'
server {
    listen 80;
    server_name da.dev-ittest.ru;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name da.dev-ittest.ru;

    ssl_certificate /etc/letsencrypt/live/da.dev-ittest.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/da.dev-ittest.ru/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
```

### 3. Активируйте конфигурацию

```bash
sudo ln -sf /etc/nginx/sites-available/da.dev-ittest.ru /etc/nginx/sites-enabled/da.dev-ittest.ru
```

### 4. Проверьте конфигурацию

```bash
sudo nginx -t
```

Должно быть: `nginx: configuration file /etc/nginx/nginx.conf test is successful`

### 5. Перезагрузите nginx

```bash
sudo systemctl reload nginx
```

### 6. Проверьте статус

```bash
sudo systemctl status nginx
curl -k https://da.dev-ittest.ru
```

## Альтернативное решение (если проблема в сети Docker)

Если nginx не может достучаться до `127.0.0.1:5001`, возможно нужно использовать IP контейнера:

```bash
# Узнайте IP контейнера
docker inspect da_app_prod | grep IPAddress

# Используйте этот IP в proxy_pass вместо 127.0.0.1:5001
```

Или используйте имя сервиса Docker, если nginx тоже в Docker:

```nginx
proxy_pass http://da_app_prod:5001;
```

## Проверка логов

```bash
# Логи nginx
sudo tail -f /var/log/nginx/error.log

# Логи приложения
cd /opt/device_accounting
docker-compose -f docker-compose.prod.yml logs -f app
```

