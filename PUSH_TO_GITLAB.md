# Как запушить код в GitLab

## Вариант 1: Через HTTPS с токеном доступа (рекомендуется)

1. Создайте токен доступа в GitLab:
   - Откройте: https://code.dev-ittest.ru/-/user_settings/personal_access_tokens
   - Создайте токен с правами `write_repository`
   - Скопируйте токен

2. Запушите код:
   ```bash
   git push https://oauth2:ВАШ_ТОКЕН@code.dev-ittest.ru/ittest/device-accounting/da-python.git main
   ```

   Или добавьте токен в URL:
   ```bash
   git remote set-url gitlab https://oauth2:ВАШ_ТОКЕН@code.dev-ittest.ru/ittest/device-accounting/da-python.git
   git push gitlab main
   ```

## Вариант 2: Через SSH (нужен SSH ключ)

1. Сгенерируйте SSH ключ (если еще нет):
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. Добавьте публичный ключ в GitLab:
   - Откройте: https://code.dev-ittest.ru/-/user_settings/ssh_keys
   - Скопируйте содержимое `~/.ssh/id_ed25519.pub`
   - Добавьте ключ

3. Запушите код:
   ```bash
   git remote set-url gitlab git@code.dev-ittest.ru:ittest/device-accounting/da-python.git
   git push gitlab main
   ```

## Текущий статус

✅ Коммит создан: `Add GitLab CI/CD pipeline for auto-deployment via external IP 91.193.239.177:2022`  
⏳ Ожидается push в GitLab

После push pipeline автоматически запустится и задеплоит приложение на сервер.

