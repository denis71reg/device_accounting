# Инструкция по развертыванию Device Accounting

## Требования

- Docker и Docker Compose
- Минимум 512MB RAM
- 1GB свободного места на диске

## Быстрый старт

### 1. Клонирование и подготовка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd device_accounting

# Создайте файл .env на основе примера
cp env.example .env

# Отредактируйте .env и установите SECRET_KEY
# Сгенерируйте секретный ключ:
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Настройка переменных окружения

Отредактируйте файл `.env`:

```env
FLASK_ENV=production
SECRET_KEY=<сгенерированный-секретный-ключ>
DATABASE_URL=sqlite:///instance/devices.db
APP_PORT=5001
```

### 3. Сборка и запуск

```bash
# Сборка образа
docker-compose -f docker-compose.prod.yml build

# Запуск приложения
docker-compose -f docker-compose.prod.yml up -d

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. Инициализация базы данных

```bash
# Выполните миграции
docker-compose -f docker-compose.prod.yml exec app flask db upgrade

# Создайте первого супер-администратора
docker-compose -f docker-compose.prod.yml exec app flask create-superadmin \
  email@ittest-team.ru "ФИО" --password
```

### 5. Доступ к приложению

Приложение будет доступно по адресу: `http://your-server-ip:5001`

## Управление

### Остановка

```bash
docker-compose -f docker-compose.prod.yml down
```

### Перезапуск

```bash
docker-compose -f docker-compose.prod.yml restart
```

### Обновление

```bash
# Остановите контейнер
docker-compose -f docker-compose.prod.yml down

# Обновите код
git pull

# Пересоберите образ
docker-compose -f docker-compose.prod.yml build

# Запустите снова
docker-compose -f docker-compose.prod.yml up -d

# Примените миграции (если есть)
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### Резервное копирование базы данных

```bash
# SQLite база данных находится в ./instance/devices.db
# Создайте резервную копию:
cp instance/devices.db instance/devices.db.backup-$(date +%Y%m%d-%H%M%S)
```

### Восстановление из резервной копии

```bash
# Остановите приложение
docker-compose -f docker-compose.prod.yml down

# Восстановите базу данных
cp instance/devices.db.backup-YYYYMMDD-HHMMSS instance/devices.db

# Запустите приложение
docker-compose -f docker-compose.prod.yml up -d
```

## Настройка Nginx (опционально)

Для использования Nginx как reverse proxy создайте файл `/etc/nginx/sites-available/da`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/da /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/HTTPS (опционально)

Для настройки HTTPS используйте Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Мониторинг

### Просмотр логов

```bash
# Все логи
docker-compose -f docker-compose.prod.yml logs

# Логи в реальном времени
docker-compose -f docker-compose.prod.yml logs -f

# Логи за последние 100 строк
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Проверка состояния

```bash
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Использование ресурсов
docker stats da_app_prod

# Логи приложения (реальное время)
tail -f instance/logs/app.log
```

## Безопасность

1. **Всегда меняйте SECRET_KEY** в продакшене
2. Используйте HTTPS в продакшене
3. Регулярно обновляйте зависимости: `pip list --outdated`
4. Делайте резервные копии базы данных
5. Ограничьте доступ к порту 5001 только через Nginx

## Устранение неполадок

### Приложение не запускается

```bash
# Проверьте логи
docker-compose -f docker-compose.prod.yml logs app

# Проверьте, что порт не занят
netstat -tulpn | grep 5001
```

### Ошибки базы данных

```bash
# Проверьте права доступа к файлу базы данных
ls -la instance/devices.db

# Выполните миграции вручную
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### Проблемы с правами доступа

```bash
# Убедитесь, что директория instance доступна для записи
chmod 755 instance
chown -R $USER:$USER instance
```

## Поддержка

При возникновении проблем обращайтесь в техподдержку IT Test.


