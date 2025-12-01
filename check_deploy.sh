#!/usr/bin/expect -f

set timeout 30
set server "ittest@192.168.16.44"
set password "adXovByUUm6yJ88f"

puts "🔍 Проверка статуса деплоя..."
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
send "cd /opt/device_accounting\r"
expect "$ "

puts "📊 Статус контейнеров:"
send "docker-compose -f docker-compose.prod.yml ps\r"
expect "$ "

puts ""
puts "📝 Последние логи приложения:"
send "docker-compose -f docker-compose.prod.yml logs --tail=30 app\r"
expect "$ "

puts ""
puts "🌐 Проверка доступности:"
send "curl -s -o /dev/null -w 'HTTP Status: %{http_code}\n' http://localhost:5001 || echo 'Приложение не отвечает'\r"
expect "$ "

send "exit\r"
expect eof


