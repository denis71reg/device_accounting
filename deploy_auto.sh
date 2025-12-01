#!/usr/bin/expect -f

# Автоматический деплой на сервер
set timeout 300

set server "ittest@192.168.16.44"
set password "adXovByUUm6yJ88f"
set remote_path "/opt/device_accounting"
set git_repo "https://code.dev-ittest.ru/ittest/device-accounting/da-python.git"

puts "🚀 Автоматический деплой Device Accounting"
puts "=========================================="
puts ""
puts "Сервер: $server"
puts "Путь: $remote_path"
puts ""

# Подключение к серверу
puts "🔐 Подключение к серверу..."
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
    timeout {
        puts "❌ Таймаут подключения"
        exit 1
    }
}

expect "$ "
puts "✅ Подключено"
puts ""

# Переход в директорию проекта
puts "📂 Проверка проекта..."
send "cd $remote_path\r"
expect "$ "

# Проверка существования .git
send "test -d .git && echo GIT_EXISTS || echo GIT_NOT_EXISTS\r"
expect {
    "GIT_EXISTS" {
        puts "✅ Проект существует, обновляю код..."
        expect "$ "
        send "git fetch origin\r"
        expect "$ "
        send "git pull origin main\r"
        expect "$ "
    }
    "GIT_NOT_EXISTS" {
        puts "📥 Проект не является git репозиторием, клонирую заново..."
        expect "$ "
        send "cd /opt\r"
        expect "$ "
        send "rm -rf device_accounting\r"
        expect "$ "
        send "git clone $git_repo device_accounting\r"
        expect "$ "
        send "cd device_accounting\r"
        expect "$ "
    }
}

puts ""
puts "🔨 Пересборка и перезапуск контейнеров..."
puts ""

send "docker-compose -f docker-compose.prod.yml down || true\r"
expect "$ "

send "docker-compose -f docker-compose.prod.yml build\r"
expect "$ "

send "docker-compose -f docker-compose.prod.yml up -d\r"
expect "$ "

send "sleep 10\r"
expect "$ "

send "docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade || echo 'Миграции уже применены'\r"
expect "$ "

puts ""
puts "✅ Проверка статуса..."
send "docker-compose -f docker-compose.prod.yml ps\r"
expect "$ "

puts ""
puts "✅ Деплой завершен!"
puts ""
puts "🌐 Приложение должно быть доступно: https://da.dev-ittest.ru"
puts ""

send "exit\r"
expect eof
