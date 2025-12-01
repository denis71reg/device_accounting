# DA · Device Accounting

Веб‑приложение для учета девайсов компании IT Test: склады, сотрудники, выдача, возврат и история.

## Стек
- Flask 3 + Blueprints
- SQLAlchemy + Flask-Migrate
- Flask-Login для аутентификации
- Bootstrap 5 интерфейс
- Docker/Gunicorn для продакшена

## Быстрый старт

### Локальная разработка

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=da.app
flask db upgrade
flask seed
flask run --port 5001
```

### Docker (разработка)

```bash
docker compose up --build
```

### Продакшен развертывание

См. подробную инструкцию в [DEPLOY.md](DEPLOY.md)

**Быстрый старт для продакшена:**

```bash
# 1. Настройте .env файл
cp env.example .env
# Отредактируйте .env и установите SECRET_KEY

# 2. Запустите скрипт развертывания
./deploy.sh

# 3. Создайте первого супер-администратора
docker-compose -f docker-compose.prod.yml exec app flask create-superadmin \
  email@ittest-team.ru "ФИО" --password
```

## Основные команды

### Управление базой данных
- `flask db init` — инициализация миграций
- `flask db migrate -m "описание"` — создание миграции
- `flask db upgrade` — применение миграций
- `flask db downgrade` — откат миграции

### Управление пользователями
- `flask create-superadmin email@ittest-team.ru "ФИО" --password` — создание супер-администратора
- `flask set-user-role email@ittest-team.ru super_admin` — изменение роли пользователя

### Данные
- `flask seed` — создание базовых локаций и типов девайсов

### Тесты
- `pytest` — запуск тестов
- `pytest -q` — тихий режим

## Структура проекта

```
device_accounting/
├── da/                    # Основное приложение
│   ├── models.py          # Модели данных
│   ├── routes/            # Маршруты (blueprints)
│   ├── templates/         # Шаблоны
│   ├── services/          # Бизнес-логика
│   └── config.py          # Конфигурация
├── migrations/            # Миграции базы данных
├── instance/              # Данные приложения (БД)
├── Dockerfile             # Docker образ
├── docker-compose.prod.yml # Docker Compose для продакшена
├── deploy.sh              # Скрипт развертывания
└── DEPLOY.md              # Инструкция по развертыванию
```

## Роли пользователей

- **Супер-админ** — полный доступ, включая удаление и просмотр истории
- **Админ** — создание и редактирование, без удаления
- **Пользователь** — только просмотр

## Обновление приложения

См. подробную инструкцию в [UPDATE.md](UPDATE.md)

**Быстрое обновление:**

```bash
# Полное обновление (рекомендуется для релизов)
./update.sh

# Быстрый хот-фикс (для срочных исправлений)
./hotfix.sh
```

**Что делают скрипты:**
- `update.sh` — полное обновление с пересборкой образа и миграциями
- `hotfix.sh` — быстрое обновление кода без пересборки

## Безопасность

- Регистрация только для email @ittest-team.ru
- CSRF защита включена
- Пароли хранятся в хешированном виде
- Аудит всех действий (для супер-админов)

## Логирование

- Логи пишутся в `instance/logs/app.log` и одновременно выводятся в консоль
- Просмотр в real-time: `tail -f instance/logs/app.log`
- Уровень логирования настраивается через переменную `LOG_LEVEL`

## Тестирование

Проект покрыт автоматическими тестами для всего функционала. Тесты запускаются автоматически перед каждым деплоем и обновлением.

```bash
# Запуск всех тестов
./run_tests.sh

# Или напрямую через pytest
pytest

# С отчетом о покрытии кода
pytest --cov=da --cov-report=html
```

**Важно:** Деплой и обновление не выполнятся, если тесты не пройдут.

Подробнее: [TESTING.md](TESTING.md)

## Документация

- [DEPLOY.md](DEPLOY.md) — развертывание на сервере
- [UPDATE.md](UPDATE.md) — процесс обновления и хот-фиксов
- [TESTING.md](TESTING.md) — руководство по тестированию
- [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) — чеклист развертывания

## Поддержка

При возникновении проблем обращайтесь в техподдержку IT Test.
