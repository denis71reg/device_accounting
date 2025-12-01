#!/bin/bash

echo "🚀 Запуск Device Accounting локально..."
echo ""

cd "$(dirname "$0")"

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Активация виртуального окружения
echo "📦 Активация виртуального окружения..."
source venv/bin/activate

# Проверка установленных пакетов
if ! python -c "import flask" 2>/dev/null; then
    echo "❌ Flask не установлен!"
    echo "Установите зависимости: pip install -r requirements.txt"
    exit 1
fi

# Проверка порта
if lsof -i :5001 &>/dev/null; then
    echo "⚠️  Порт 5001 уже занят!"
    echo "Остановите другой процесс или используйте другой порт"
    lsof -i :5001
    read -p "Остановить процесс на порту 5001? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti :5001 | xargs kill -9 2>/dev/null
        sleep 2
    else
        exit 1
    fi
fi

# Применение миграций
echo "🗄️  Применение миграций..."
export FLASK_APP=da.app
flask db upgrade 2>/dev/null || echo "⚠️  Миграции уже применены или ошибка"

# Запуск сервера
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Запуск сервера..."
echo ""
echo "📍 Адрес: http://127.0.0.1:5001"
echo "📍 Или:   http://localhost:5001"
echo ""
echo "⏹️  Нажмите Ctrl+C для остановки"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

flask run --host=127.0.0.1 --port=5001




