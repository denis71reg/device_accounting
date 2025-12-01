#!/usr/bin/expect -f

set timeout 30
set server "ittest@192.168.16.44"
set password "adXovByUUm6yJ88f"

puts "🔧 Исправление конфигурации nginx..."
puts ""

spawn ssh -o StrictHostKeyChecking=no $server

expect {
    "password:" {
        send "$password\r"
    }
    "yes/no" {
        send "yes\r"
        expect "password:"
        send "$password\r"
    }
}

expect "$ "

puts "📋 Проверка текущей конфигурации nginx:"
send "cat /etc/nginx/sites-enabled/da.dev-ittest.ru 2>/dev/null || cat /etc/nginx/conf.d/da.dev-ittest.ru.conf 2>/dev/null || echo 'Конфиг не найден, создаю...'\r"
expect "$ "

puts ""
puts "🔍 Проверка доступности приложения:"
send "curl -v http://localhost:5001 2>&1 | head -15\r"
expect "$ "

puts ""
puts "📝 Создание правильной конфигурации nginx..."
send "sudo tee /etc/nginx/sites-available/da.dev-ittest.ru > /dev/null << 'NGINX_EOF'
server {
    listen 80;
    server_name da.dev-ittest.ru;

    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name da.dev-ittest.ru;

    ssl_certificate /etc/letsencrypt/live/da.dev-ittest.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/da.dev-ittest.ru/privkey.pem;

    # Security headers
    add_header X-Frame-Options \"SAMEORIGIN\" always;
    add_header X-Content-Type-Options \"nosniff\" always;
    add_header X-XSS-Protection \"1; mode=block\" always;

    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \"upgrade\";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
NGINX_EOF
\r"
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "$ " {
        # continue
    }
}

expect "$ "

puts ""
puts "🔗 Активация конфигурации:"
send "sudo ln -sf /etc/nginx/sites-available/da.dev-ittest.ru /etc/nginx/sites-enabled/da.dev-ittest.ru\r"
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "$ " {
        # continue
    }
}

expect "$ "

puts ""
puts "✅ Проверка конфигурации nginx:"
send "sudo nginx -t\r"
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "$ " {
        # continue
    }
}

expect "$ "

puts ""
puts "🔄 Перезагрузка nginx:"
send "sudo systemctl reload nginx\r"
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "$ " {
        # continue
    }
}

expect "$ "

puts ""
puts "✅ Проверка статуса nginx:"
send "sudo systemctl status nginx --no-pager | head -5\r"
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "$ " {
        # continue
    }
}

expect "$ "

puts ""
puts "🌐 Тест доступности:"
send "curl -k -s -o /dev/null -w 'HTTPS Status: %{http_code}\n' https://da.dev-ittest.ru || echo 'Ошибка'\r"
expect "$ "

send "exit\r"
expect eof

