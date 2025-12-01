# Быстрое исправление: сервер не запускается

## Проблема
Не удаётся установить соединение с сайтом на 127.0.0.1

## Решение

### Вариант 1: Автоматический запуск (рекомендуется)

На сервере выполните:
```bash
cd /opt/device_accounting
./start_server.sh
```

### Вариант 2: Ручной запуск

```bash
cd /opt/device_accounting

# 1. Проверить статус
docker-compose -f docker-compose.prod.yml ps

# 2. Остановить все контейнеры
docker-compose -f docker-compose.prod.yml down

# 3. Запустить заново
docker-compose -f docker-compose.prod.yml up -d

# 4. Подождать 10 секунд
sleep 10

# 5. Применить миграции
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# 6. Проверить логи
docker-compose -f docker-compose.prod.yml logs app --tail=50
```

### Вариант 3: Полная пересборка

Если проблема сохраняется:
```bash
cd /opt/device_accounting

# Остановить
docker-compose -f docker-compose.prod.yml down

# Удалить старые образы
docker-compose -f docker-compose.prod.yml rm -f
docker rmi $(docker images | grep device_accounting | awk '{print $3}') || true

# Пересобрать
docker-compose -f docker-compose.prod.yml build --no-cache

# Запустить
docker-compose -f docker-compose.prod.yml up -d

# Применить миграции
sleep 10
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# Проверить
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs app
```

## Проверка

После запуска проверьте:

```bash
# 1. Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# 2. Логи
docker-compose -f docker-compose.prod.yml logs app --tail=50

# 3. Доступность приложения
curl http://127.0.0.1:5001

# 4. Доступность через Nginx
curl http://127.0.0.1:2022
```

## Диагностика

Если сервер все еще не запускается, выполните диагностику:

```bash
cd /opt/device_accounting
./check_server.sh
```

Или вручную:

```bash
# Проверить, что контейнер запущен
docker-compose -f docker-compose.prod.yml ps

# Проверить логи на ошибки
docker-compose -f docker-compose.prod.yml logs app | grep -i error

# Проверить, что приложение внутри контейнера работает
docker-compose -f docker-compose.prod.yml exec app python -c "from da import create_app; app = create_app(); print('OK')"

# Проверить порты
sudo ss -tlnp | grep 5001
sudo ss -tlnp | grep 2022
```

## Частые проблемы

### Проблема: Контейнер падает сразу после запуска
**Решение:** Проверьте логи и переменные окружения:
```bash
docker-compose -f docker-compose.prod.yml logs app
docker-compose -f docker-compose.prod.yml exec app env | grep -E "FLASK|DATABASE|SECRET"
```

### Проблема: Порт уже занят
**Решение:** Найдите и остановите процесс:
```bash
sudo lsof -i :5001
sudo kill -9 <PID>
```

### Проблема: Ошибка миграции
**Решение:** Примените миграции вручную:
```bash
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### Проблема: База данных заблокирована
**Решение:** Перезапустите контейнеры:
```bash
docker-compose -f docker-compose.prod.yml restart
```




