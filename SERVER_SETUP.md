# Инструкция по развертыванию на сервере

## Вариант 1: Через Git (рекомендуется)

### На вашем компьютере:

1. **Подготовьте код:**
   ```bash
   # Убедитесь, что все закоммичено
   git add .
   git commit -m "Готово к продакшену"
   git push origin main
   ```

### На сервере:

2. **Подключитесь к серверу:**
   ```bash
   ssh user@your-server-ip
   ```

3. **Клонируйте репозиторий (если еще не клонирован):**
   ```bash
   cd /opt  # или другая директория
   git clone <your-repository-url> device_accounting
   cd device_accounting
   ```

4. **Или обновите существующий:**
   ```bash
   cd /path/to/device_accounting
   git pull
   ```

5. **Настройте сервер:**
   ```bash
   chmod +x setup_server.sh deploy.sh update.sh hotfix.sh
   ./setup_server.sh
   ```

6. **Отредактируйте .env:**
   ```bash
   nano .env
   # Установите SECRET_KEY (сгенерируйте: python -c "import secrets; print(secrets.token_hex(32))")
   ```

7. **Запустите развертывание:**
   ```bash
   ./deploy.sh
   ```

8. **Создайте первого супер-администратора:**
   ```bash
   docker-compose -f docker-compose.prod.yml exec app flask create-superadmin \
     email@ittest-team.ru "ФИО" --password
   ```

## Вариант 2: Через SCP (если нет Git на сервере)

### На вашем компьютере:

1. **Создайте архив проекта:**
   ```bash
   # Исключите ненужные файлы
   tar --exclude='.git' \
       --exclude='venv' \
       --exclude='__pycache__' \
       --exclude='*.pyc' \
       --exclude='instance' \
       -czf device_accounting.tar.gz .
   ```

2. **Скопируйте на сервер:**
   ```bash
   scp device_accounting.tar.gz user@your-server-ip:/tmp/
   ```

### На сервере:

3. **Распакуйте:**
   ```bash
   cd /opt
   mkdir -p device_accounting
   cd device_accounting
   tar -xzf /tmp/device_accounting.tar.gz
   ```

4. **Продолжите с шага 5 из Варианта 1**

## Вариант 3: Через rsync (для обновлений)

### На вашем компьютере:

```bash
rsync -avz --exclude '.git' \
          --exclude 'venv' \
          --exclude '__pycache__' \
          --exclude 'instance' \
          --exclude '*.pyc' \
          ./ user@your-server-ip:/opt/device_accounting/
```

### На сервере:

```bash
cd /opt/device_accounting
./update.sh
```

## Быстрая команда для копирования

Если у вас есть доступ по SSH, можете использовать эту команду (замените данные):

```bash
# С вашего компьютера
rsync -avz --exclude '.git' --exclude 'venv' --exclude '__pycache__' --exclude 'instance' \
  ./ user@server-ip:/opt/device_accounting/ && \
ssh user@server-ip "cd /opt/device_accounting && ./update.sh"
```

## Настройка доступа по внешнему IP (Nginx)

После развертывания приложения настройте Nginx для доступа по внешнему IP:

```bash
# На сервере
cd /opt/device_accounting
sudo ./setup_nginx.sh
```

Скрипт автоматически:
- Установит Nginx (если не установлен)
- Создаст конфигурацию для порта 2022
- Настроит проксирование на приложение (localhost:5001)
- Перезапустит Nginx

**Важно:** Убедитесь, что порт 2022 открыт в firewall:
```bash
sudo ufw allow 2022/tcp
```

После настройки приложение будет доступно по адресу:
- `http://91.193.239.177:2022`

## Проверка после развертывания

```bash
# На сервере
curl http://localhost:5001/
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f

# Проверка Nginx
sudo systemctl status nginx
sudo tail -f /var/log/nginx/da_access.log
```

## Настройка автоматического обновления

Если хотите автоматизировать через GitHub Actions, см. `.github/workflows/deploy.yml.example`

## Нужна помощь?

Если возникнут проблемы:
1. Проверьте логи: `docker-compose -f docker-compose.prod.yml logs`
2. Проверьте статус: `docker-compose -f docker-compose.prod.yml ps`
3. Обратитесь в техподдержку IT Test


