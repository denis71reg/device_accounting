#!/usr/bin/expect -f

set timeout 30
set server "ittest@192.168.16.44"
set password "adXovByUUm6yJ88f"

puts "🔍 Диагностика ошибки 502 Bad Gateway..."
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

puts "1️⃣ Проверка статуса контейнеров:"
send "cd /opt/device_accounting && docker-compose -f docker-compose.prod.yml ps\r"
expect "$ "

puts ""
puts "2️⃣ Проверка доступности приложения внутри контейнера:"
send "docker-compose -f docker-compose.prod.yml exec -T app curl -s -o /dev/null -w 'HTTP: %{http_code}\n' http://localhost:5001 || echo 'Ошибка подключения'\r"
expect "$ "

puts ""
puts "3️⃣ Проверка доступности с хоста:"
send "curl -s -o /dev/null -w 'HTTP: %{http_code}\n' http://localhost:5001 || echo 'Ошибка подключения'\r"
expect "$ "

puts ""
puts "4️⃣ Проверка конфигурации nginx:"
send "sudo cat /etc/nginx/sites-enabled/da.dev-ittest.ru 2>/dev/null || sudo cat /etc/nginx/conf.d/da.dev-ittest.ru.conf 2>/dev/null || echo 'Конфиг не найден'\r"
expect "$ "

puts ""
puts "5️⃣ Проверка статуса nginx:"
send "sudo systemctl status nginx --no-pager | head -10\r"
expect "$ "

puts ""
puts "6️⃣ Последние логи приложения:"
send "cd /opt/device_accounting && docker-compose -f docker-compose.prod.yml logs --tail=20 app\r"
expect "$ "

puts ""
puts "7️⃣ Проверка портов:"
send "sudo netstat -tlnp | grep -E ':(80|443|5001)' || ss -tlnp | grep -E ':(80|443|5001)'\r"
expect "$ "

send "exit\r"
expect eof

