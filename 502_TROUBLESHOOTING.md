# Устранение ошибки 502 Bad Gateway

## Описание проблемы

Ошибка **502 Bad Gateway** означает, что nginx не может подключиться к приложению Flask на порту 5001. Это происходит когда:

1. Docker контейнер с приложением не запущен
2. Контейнер упал или перезапускается
3. Приложение внутри контейнера не слушает порт 5001
4. Проблемы с сетью между nginx и контейнером

## Быстрое решение

На сервере выполните:

```bash
cd /opt/device_accounting
chmod +x fix_502.sh
./fix_502.sh
```

Этот скрипт автоматически:
- Проверит статус контейнеров и nginx
- Пересоберет и запустит приложение
- Применит миграции
- Проверит доступность

## Ручная диагностика

### Шаг 1: Проверка статуса контейнеров

```bash
cd /opt/device_accounting
docker-compose -f docker-compose.prod.yml ps
```

**Ожидаемый результат:** Контейнер `da_app_prod` должен быть в статусе `Up`

**Если контейнер не запущен:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

**Если контейнер в статусе `Restarting` или `Exited`:**
```bash
# Посмотреть логи ошибок
docker-compose -f docker-compose.prod.yml logs app --tail=50
```

### Шаг 2: Проверка логов приложения

```bash
docker-compose -f docker-compose.prod.yml logs app --tail=50
```

Ищите ошибки:
- `ModuleNotFoundError` - проблема с зависимостями
- `Address already in use` - порт занят
- `database is locked` - проблема с базой данных
- `SECRET_KEY` - не установлен ключ

### Шаг 3: Проверка порта 5001

```bash
# Проверить, слушается ли порт
sudo ss -tlnp | grep 5001
# или
sudo netstat -tlnp | grep 5001
```

**Ожидаемый результат:** Должен быть процесс, слушающий порт 5001

**Если порт не слушается:**
- Контейнер не запущен или упал
- Проверьте логи (шаг 2)

### Шаг 4: Проверка доступности приложения

```bash
# Проверка изнутри контейнера
docker-compose -f docker-compose.prod.yml exec app curl http://127.0.0.1:5001

# Проверка с хоста
curl http://127.0.0.1:5001
```

**Ожидаемый результат:** Должен вернуться HTML код страницы

**Если не работает:**
- Приложение не запустилось внутри контейнера
- Проверьте логи (шаг 2)

### Шаг 5: Проверка nginx

```bash
# Проверка статуса
sudo systemctl status nginx

# Проверка логов ошибок
sudo tail -50 /var/log/nginx/da_error.log

# Проверка конфигурации
sudo nginx -t
```

**Если nginx не запущен:**
```bash
sudo systemctl start nginx
```

**Если ошибки в логах:**
- Проверьте, что приложение доступно на порту 5001 (шаг 4)
- Проверьте конфигурацию nginx в `/etc/nginx/sites-available/da` или `/etc/nginx/nginx.conf`

### Шаг 6: Перезапуск всего стека

Если ничего не помогло, выполните полный перезапуск:

```bash
cd /opt/device_accounting

# Остановка
docker-compose -f docker-compose.prod.yml down

# Проверка .env
if [ ! -f .env ]; then
    cp env.example .env
    echo "⚠️  Отредактируйте .env и установите SECRET_KEY"
    exit 1
fi

# Создание директорий
mkdir -p instance logs
chmod 755 instance logs

# Пересборка и запуск
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Ожидание запуска
sleep 15

# Применение миграций
docker-compose -f docker-compose.prod.yml exec -T app flask db upgrade

# Перезагрузка nginx
sudo systemctl reload nginx
```

## Частые проблемы и решения

### Проблема 1: Контейнер сразу падает

**Симптомы:** Контейнер показывает статус `Exited` или постоянно перезапускается

**Решение:**
```bash
# Посмотреть логи
docker-compose -f docker-compose.prod.yml logs app

# Проверить переменные окружения
docker-compose -f docker-compose.prod.yml exec app env | grep -E "FLASK|DATABASE|SECRET"

# Попробовать запустить вручную
docker-compose -f docker-compose.prod.yml run --rm app python -c "from da import create_app; app = create_app(); print('OK')"
```

**Возможные причины:**
- Не установлен `SECRET_KEY` в `.env`
- Ошибка в коде приложения
- Проблемы с базой данных

### Проблема 2: Порт 5001 занят другим процессом

**Симптомы:** Ошибка `port is already allocated` или `address already in use`

**Решение:**
```bash
# Найти процесс, использующий порт
sudo lsof -i :5001
# или
sudo ss -tlnp | grep 5001

# Остановить процесс
sudo kill -9 <PID>

# Или изменить порт в docker-compose.prod.yml
```

### Проблема 3: Nginx не может подключиться к приложению

**Симптомы:** В логах nginx: `connect() failed (111: Connection refused)`

**Решение:**
1. Убедитесь, что контейнер запущен: `docker-compose -f docker-compose.prod.yml ps`
2. Проверьте, что порт 5001 слушается: `sudo ss -tlnp | grep 5001`
3. Проверьте доступность: `curl http://127.0.0.1:5001`
4. Проверьте конфигурацию nginx: `sudo nginx -t`

### Проблема 4: База данных заблокирована

**Симптомы:** Ошибка `database is locked` в логах

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

**Симптомы:** `ModuleNotFoundError` или `ImportError` в логах

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
# 1. Статус контейнеров (должен быть Up)
docker-compose -f docker-compose.prod.yml ps

# 2. Логи (должны быть без ошибок)
docker-compose -f docker-compose.prod.yml logs app --tail=20

# 3. Доступность приложения
curl http://127.0.0.1:5001

# 4. Проверка через nginx
curl http://127.0.0.1:2022

# 5. Проверка внешнего доступа
curl https://da.dev-ittest.ru
```

## Сбор диагностической информации

Если проблема не решается, соберите диагностическую информацию:

```bash
cd /opt/device_accounting

{
    echo "=== Статус контейнеров ==="
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "=== Последние логи приложения ==="
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
    
    echo ""
    echo "=== Статус nginx ==="
    sudo systemctl status nginx || echo "Nginx не установлен"
    
    echo ""
    echo "=== Логи nginx (последние 50 строк) ==="
    sudo tail -50 /var/log/nginx/da_error.log 2>/dev/null || echo "Логи nginx недоступны"
} > 502_diagnostics.txt 2>&1

cat 502_diagnostics.txt
```

Пришлите содержимое файла `502_diagnostics.txt` для дальнейшей диагностики.

