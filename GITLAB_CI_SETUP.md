# Настройка GitLab CI/CD для автоматического деплоя

## Шаг 1: Настройка SSH ключа в GitLab

1. Сгенерируйте SSH ключ на сервере (если еще нет):
   ```bash
   ssh -p 2022 ittest@91.193.239.177
   ssh-keygen -t ed25519 -C "gitlab-ci@device-accounting" -f ~/.ssh/gitlab_ci_key
   ```

2. Добавьте публичный ключ на сервер:
   ```bash
   cat ~/.ssh/gitlab_ci_key.pub >> ~/.ssh/authorized_keys
   ```

3. В GitLab перейдите в **Settings → CI/CD → Variables** и добавьте:
   - **Key**: `SSH_PRIVATE_KEY`
   - **Value**: Содержимое приватного ключа (`~/.ssh/gitlab_ci_key`)
   - **Type**: Variable
   - **Protected**: ✅ (опционально)
   - **Masked**: ❌ (не маскировать, иначе не сработает)

## Шаг 2: Настройка переменных окружения (опционально)

Если нужны дополнительные переменные:
- `SERVER_HOST`: `91.193.239.177`
- `SERVER_PORT`: `2022`
- `SERVER_USER`: `ittest`
- `DEPLOY_PATH`: `/opt/device_accounting`

## Шаг 3: Первый деплой

После настройки SSH ключа, pipeline запустится автоматически при push в ветку `main` или `master`.

## Проверка работы

1. Сделайте commit и push:
   ```bash
   git add .
   git commit -m "Add GitLab CI/CD pipeline"
   git push gitlab main
   ```

2. Проверьте pipeline в GitLab: **CI/CD → Pipelines**

3. После успешного деплоя приложение будет доступно: https://da.dev-ittest.ru

## Устранение проблем

### Pipeline падает на SSH подключении
- Проверьте, что SSH ключ добавлен правильно в GitLab Variables
- Убедитесь, что публичный ключ добавлен в `~/.ssh/authorized_keys` на сервере
- Проверьте права доступа: `chmod 600 ~/.ssh/gitlab_ci_key`

### Контейнеры не запускаются
- Проверьте логи: `docker-compose -f docker-compose.prod.yml logs`
- Убедитесь, что порт 5001 свободен
- Проверьте, что файл `.env` существует на сервере

### Nginx возвращает 502
- См. инструкцию в `FIX_502_NGINX.md`
- Проверьте конфигурацию nginx на сервере

