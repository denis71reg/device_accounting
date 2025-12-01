# Запуск приложения локально

## Быстрый запуск

### Вариант 1: Автоматический скрипт

```bash
cd /Users/denische/Documents/device_accounting
./start_local.sh
```

### Вариант 2: Ручной запуск

```bash
cd /Users/denische/Documents/device_accounting

# 1. Активировать виртуальное окружение
source venv/bin/activate

# 2. Установить переменную окружения
export FLASK_APP=da.app

# 3. Применить миграции (если нужно)
flask db upgrade

# 4. Запустить сервер
flask run --host=127.0.0.1 --port=5001
```

### Вариант 3: Запуск в фоне

```bash
cd /Users/denische/Documents/device_accounting
source venv/bin/activate
export FLASK_APP=da.app

# Запустить в фоне
nohup flask run --host=127.0.0.1 --port=5001 > /tmp/flask_server.log 2>&1 &

# Проверить, что запустился
sleep 3
curl http://127.0.0.1:5001

# Посмотреть логи
tail -f /tmp/flask_server.log

# Остановить
pkill -f "flask run"
```

## Проверка

После запуска откройте в браузере:
- http://127.0.0.1:5001
- http://localhost:5001

## Остановка сервера

### Если запущен в терминале:
Нажмите `Ctrl+C`

### Если запущен в фоне:
```bash
# Найти процесс
ps aux | grep "flask run"

# Остановить
pkill -f "flask run"

# Или по PID
kill <PID>
```

## Режим отладки

Для запуска с отладкой и автоматической перезагрузкой:

```bash
source venv/bin/activate
export FLASK_APP=da.app
export FLASK_ENV=development
flask run --host=127.0.0.1 --port=5001 --debug
```

## Проблемы

### Порт 5001 занят

```bash
# Найти процесс
lsof -i :5001

# Остановить
kill -9 <PID>

# Или использовать другой порт
flask run --host=127.0.0.1 --port=5002
```

### Ошибка "Module not found"

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### Ошибка миграции

```bash
# Проверить текущую версию
flask db current

# Применить миграции
flask db upgrade
```




