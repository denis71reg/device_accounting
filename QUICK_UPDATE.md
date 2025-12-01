# Быстрая шпаргалка по обновлению

## 🚀 Полное обновление (релиз)

```bash
./update.sh
```

**Используйте когда:**
- Новый релиз
- Изменения в зависимостях
- Изменения в Dockerfile
- Структурные изменения БД

## 🔥 Быстрый хот-фикс

```bash
./hotfix.sh
```

**Используйте когда:**
- Исправление багов
- Изменения в коде/шаблонах
- Срочные исправления

## 📋 Ручные команды

### Обновление через git + Docker

```bash
# 1. Резервная копия
cp instance/devices.db instance/devices.db.backup-$(date +%Y%m%d-%H%M%S)

# 2. Обновление кода
git pull

# 3. Пересборка и запуск
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 4. Миграции
docker-compose -f docker-compose.prod.yml exec app flask db upgrade
```

### Только код (без пересборки)

```bash
git pull
docker-compose -f docker-compose.prod.yml cp . app:/app/
docker-compose -f docker-compose.prod.yml restart app
```

## 🔙 Откат

```bash
# Откат кода
git checkout <commit-hash>

# Восстановление БД
cp instance/devices.db.backup-YYYYMMDD-HHMMSS instance/devices.db

# Перезапуск
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Проверка после обновления

```bash
# Логи
docker-compose -f docker-compose.prod.yml logs -f

# Статус
docker-compose -f docker-compose.prod.yml ps

# Доступность
curl http://localhost:5001/
```

## ⚠️ Важно

- Всегда делайте резервную копию БД перед обновлением
- Проверяйте логи после обновления
- Тестируйте критичные функции после обновления





