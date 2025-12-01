# Сервер не запускается - Пошаговое решение

## Проблема
Не удаётся установить соединение с сайтом на 127.0.0.1

## Автоматическое исправление (рекомендуется)

На сервере выполните одну команду:

```bash
cd /opt/device_accounting
./fix_server.sh
```

Этот скрипт:
- Остановит все контейнеры
- Пересоберет образ
- Запустит сервер
- Применит миграции
- Проверит доступность

## Ручное исправление

Если автоматический скрипт не помог, выполните пошагово:

### Шаг 1: Проверка текущего состояния

```bash
cd /opt/device_accounting

# Проверить статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Проверить логи
docker-compose -f docker-compose.prod.yml logs app --tail=50
```

### Шаг 2: Остановка и очистка

```bash
# Остановить все контейнеры
docker-compose -f docker-compose.prod.yml down

# Удалить старые контейнеры (если нужно)
docker-compose -f docker-compose.prod.yml rm -f

# Очистить неиспользуемые образы (опционально)
docker system prune -f
```

### Шаг 3: Проверка конфигурации

```bash
# Проверить наличие .env
ls -la .env

# Если нет .env, создать из примера
if [ ! -f .env ]; then
    cp env.example .env
    echo "⚠️  Отредактируйте .env и установите SECRET_KEY"
    echo "   Сгенерировать ключ: python3 -c \"import secrets; print(secrets.token_hex(32))\""
    exit 1
fi

# Проверить, что SECRET_KEY установлен
grep -q "SECRET_KEY=" .env && echo "✅ SECRET_KEY найден" || echo "❌ SECRET_KEY не найден!"
```

### Шаг 4: Создание директорий

```bash
mkdir -p instance logs
chmod 755 instance
chmod 755 logs
```

### Шаг 5: Пересборка и запуск

```bash
# Пересобрать образ
docker-compose -f docker-compose.prod.yml build --no-cache

# Запустить контейнеры
docker-compose -f docker-compose.prod.yml up -d

# Подождать 15 секунд
sleep 15
```

### Шаг 6: Применение миграций

```bash
# Применить миграции
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### Шаг 7: Проверка

```bash
# Проверить статус
docker-compose -f docker-compose.prod.yml ps

# Проверить логи
docker-compose -f docker-compose.prod.yml logs app --tail=50

# Проверить доступность
curl -v http://127.0.0.1:5001
```

## Диагностика проблем

### Проблема 1: Контейнер сразу падает

**Симптомы:** Контейнер показывает статус "Exited" или "Restarting"

**Решение:**
```bash
# Посмотреть логи ошибок
docker-compose -f docker-compose.prod.yml logs app

# Проверить переменные окружения
docker-compose -f docker-compose.prod.yml exec app env | grep -E "FLASK|DATABASE|SECRET"

# Попробовать запустить вручную внутри контейнера
docker-compose -f docker-compose.prod.yml run --rm app python -c "from da import create_app; app = create_app(); print('OK')"
```

### Проблема 2: Порт занят

**Симптомы:** Ошибка "port is already allocated" или "address already in use"

**Решение:**
```bash
# Найти процесс, использующий порт
sudo lsof -i :5001
# или
sudo netstat -tlnp | grep 5001

# Остановить процесс
sudo kill -9 <PID>

# Или изменить порт в docker-compose.prod.yml
```

### Проблема 3: Ошибка миграции

**Симптомы:** Ошибки при `flask db upgrade`

**Решение:**
```bash
# Проверить текущую версию миграции
docker-compose -f docker-compose.prod.yml exec app flask db current

# Посмотреть историю миграций
docker-compose -f docker-compose.prod.yml exec app flask db history

# Попробовать применить миграцию вручную
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### Проблема 4: База данных заблокирована

**Симптомы:** Ошибка "database is locked"

**Решение:**
```bash
# Остановить все контейнеры
docker-compose -f docker-compose.prod.yml down

# Подождать 5 секунд
sleep 5

# Запустить заново
docker-compose -f docker-compose.prod.yml up -d
```

### Проблема 5: Ошибка импорта модулей

**Симптомы:** "ModuleNotFoundError" или "ImportError" в логах

**Решение:**
```bash
# Пересобрать образ без кэша
docker-compose -f docker-compose.prod.yml build --no-cache

# Проверить, что все файлы скопированы
docker-compose -f docker-compose.prod.yml exec app ls -la /app/da/
docker-compose -f docker-compose.prod.yml exec app ls -la /app/migrations/
```

## Проверка после исправления

После выполнения всех шагов проверьте:

```bash
# 1. Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# 2. Логи (должны быть без ошибок)
docker-compose -f docker-compose.prod.yml logs app --tail=20

# 3. Доступность приложения
curl http://127.0.0.1:5001

# 4. Проверка внутри контейнера
docker-compose -f docker-compose.prod.yml exec app curl http://127.0.0.1:5001
```

## Если ничего не помогло

Выполните полную диагностику и пришлите результаты:

```bash
cd /opt/device_accounting

# Соберите информацию
{
    echo "=== Статус контейнеров ==="
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "=== Последние логи ==="
    docker-compose -f docker-compose.prod.yml logs app --tail=100
    
    echo ""
    echo "=== Переменные окружения ==="
    docker-compose -f docker-compose.prod.yml exec app env | grep -E "FLASK|DATABASE|SECRET" || echo "Контейнер не запущен"
    
    echo ""
    echo "=== Версия миграции ==="
    docker-compose -f docker-compose.prod.yml exec app flask db current || echo "Не удалось проверить"
    
    echo ""
    echo "=== Проверка портов ==="
    sudo ss -tlnp | grep -E "5001|2022" || echo "Порты не слушаются"
} > server_diagnostics.txt 2>&1

cat server_diagnostics.txt
```

Пришлите содержимое файла `server_diagnostics.txt` для дальнейшей диагностики.




