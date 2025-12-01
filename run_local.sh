#!/bin/bash

# Скрипт для запуска приложения локально

cd "$(dirname "$0")"

# Активация виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Создаю..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Устанавливаю зависимости..."
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# Проверка базы данных
if [ ! -f "instance/devices.db" ]; then
    echo "📊 Инициализация базы данных..."
    export FLASK_APP=da.app
    flask db upgrade
    echo "🌱 Заполнение начальными данными..."
    flask seed
fi

# Запуск приложения
echo "🚀 Запуск приложения на http://127.0.0.1:5001"
echo ""
export FLASK_APP=da.app
export FLASK_ENV=development
flask run --host=127.0.0.1 --port=5001
