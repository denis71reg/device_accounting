# Перенос кода в GitLab

## Новый репозиторий
**GitLab:** https://code.dev-ittest.ru/ittest/device-accounting/da-python

## Вариант 1: Через HTTPS (с токеном доступа)

1. **Создайте токен доступа в GitLab:**
   - Откройте: https://code.dev-ittest.ru/-/user_settings/personal_access_tokens
   - Создайте токен с правами `write_repository`

2. **Выполните команды:**
   ```bash
   cd /Users/denische/Documents/device_accounting
   
   # Добавить GitLab remote (если еще не добавлен)
   git remote add gitlab https://code.dev-ittest.ru/ittest/device-accounting/da-python.git
   
   # Отправить код
   git push gitlab main
   # При запросе логина: ваш username
   # При запросе пароля: вставьте токен доступа
   ```

## Вариант 2: Через SSH

1. **Настройте SSH ключ в GitLab:**
   - Добавьте ваш публичный SSH ключ в GitLab: https://code.dev-ittest.ru/-/user_settings/ssh_keys

2. **Выполните команды:**
   ```bash
   cd /Users/denische/Documents/device_accounting
   
   # Добавить GitLab remote через SSH
   git remote add gitlab git@code.dev-ittest.ru:ittest/device-accounting/da-python.git
   
   # Принять SSH ключ сервера (первый раз)
   ssh-keyscan code.dev-ittest.ru >> ~/.ssh/known_hosts
   
   # Отправить код
   git push gitlab main
   ```

## Вариант 3: Сделать GitLab основным remote

После успешного переноса можно сделать GitLab основным:

```bash
# Удалить старый origin (GitHub)
git remote remove origin

# Переименовать gitlab в origin
git remote rename gitlab origin

# Или добавить оба:
git remote set-url --add --push origin https://code.dev-ittest.ru/ittest/device-accounting/da-python.git
```

## Проверка

После переноса проверьте:
- https://code.dev-ittest.ru/ittest/device-accounting/da-python

Все файлы должны быть там.

## Важно

⚠️ **Перед переносом убедитесь, что репозиторий на GitHub приватный!**
- В репозитории были пароли (уже удалены, но остались в истории)
- Сделайте GitHub репозиторий приватным: Settings → Make private


