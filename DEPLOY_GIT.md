# 🚀 Деплой через Git

## Вариант 1: Через веб-консоль сервера

### Шаг 1: Откройте веб-консоль
1. Войдите в панель управления вашего хостинг-провайдера
2. Найдите ваш сервер (IP: 91.193.239.177)
3. Откройте веб-консоль/SSH терминал

### Шаг 2: Подготовка на сервере

```bash
# Перейдите в директорию проекта (или создайте новую)
cd /opt/device_accounting  # или ваша директория

# Если проекта еще нет - клонируйте
git clone https://github.com/denis71reg/device_accounting.git .

# Если проект уже есть - обновите
git pull origin main
```

### Шаг 3: Настройка окружения

```bash
# Создайте .env файл из примера
cp env.example .env

# Сгенерируйте SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# Откройте .env и вставьте сгенерированный ключ
nano .env
# Установите: SECRET_KEY=ваш_сгенерированный_ключ
```

### Шаг 4: Запуск деплоя

```bash
# Сделайте скрипт исполняемым
chmod +x deploy_from_git.sh

# Запустите деплой
./deploy_from_git.sh
```

Или вручную:

```bash
# Создайте директории
mkdir -p instance logs

# Остановите старые контейнеры
docker-compose -f docker-compose.prod.yml down

# Соберите и запустите
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Примените миграции
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

---

## Вариант 2: Через SSH (если доступен)

Если у вас есть SSH доступ на порт 22 или другой:

```bash
# С вашего локального компьютера
ssh user@91.193.239.177

# Затем выполните шаги из Варианта 1
```

---

## Вариант 3: Попросить DevOps

Если нет доступа к веб-консоли, попросите DevOps выполнить:

1. **Клонировать/обновить репозиторий:**
   ```bash
   cd /opt/device_accounting  # или текущая директория проекта
   git pull origin main
   ```

2. **Перезапустить контейнеры:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   docker-compose -f docker-compose.prod.yml exec app flask db upgrade
   ```

---

## Обновление в будущем

После каждого обновления кода в GitHub:

```bash
cd /opt/device_accounting
git pull origin main
./deploy_from_git.sh
```

Или вручную:
```bash
cd /opt/device_accounting
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

---

## Проверка работы

```bash
# Проверка статуса контейнеров
docker-compose -f docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Проверка доступности
curl http://localhost:5001
```

---

## Важные файлы

- **`.env`** - конфигурация (SECRET_KEY, DATABASE_URL)
- **`instance/devices.db`** - база данных (сохраняется между обновлениями)
- **`docker-compose.prod.yml`** - конфигурация Docker
- **`nginx.conf`** - конфигурация Nginx (если используется)

---

## Проблемы?

1. **Ошибка "Git не установлен":**
   ```bash
   apt-get update && apt-get install -y git
   ```

2. **Ошибка "Docker не установлен":**
   ```bash
   # Установите Docker и Docker Compose
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

3. **Ошибка миграций:**
   ```bash
   # Проверьте логи
   docker-compose -f docker-compose.prod.yml logs app
   ```

4. **Приложение не запускается:**
   ```bash
   # Проверьте .env файл
   cat .env
   
   # Проверьте логи
   docker-compose -f docker-compose.prod.yml logs -f app
   ```

