# Руководство по тестированию

## Обзор

Проект покрыт автоматическими тестами для всего функционала. Тесты запускаются автоматически перед каждым деплоем и обновлением.

## Структура тестов

```
tests/
├── conftest.py              # Фикстуры и общие настройки
├── test_auth.py            # Тесты аутентификации
├── test_models.py          # Тесты моделей данных
├── test_inventory_service.py # Тесты сервиса инвентаризации
├── test_routes_employees.py # Тесты роутов сотрудников
├── test_routes_devices.py   # Тесты роутов устройств
├── test_routes_locations.py # Тесты роутов локаций
├── test_routes_audit.py     # Тесты роутов аудита
├── test_routes_dashboard.py # Тесты дашборда
└── test_forms.py           # Тесты форм и валидации
```

## Запуск тестов

### Локально

```bash
# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск с покрытием кода
pytest --cov=da --cov-report=html

# Запуск конкретного теста
pytest tests/test_auth.py::test_registration_and_login_flow
```

### Через скрипт

```bash
# Запуск всех тестов с отчетом о покрытии
./run_tests.sh
```

## Автоматический запуск

Тесты автоматически запускаются:

1. **Перед деплоем** (`./deploy.sh`) - деплой не выполнится, если тесты не пройдут
2. **Перед обновлением** (`./update.sh`) - обновление не выполнится, если тесты не пройдут
3. **Перед хот-фиксом** (`./hotfix.sh`) - можно пропустить для экстренных случаев

### Пропуск тестов (только для экстренных случаев)

```bash
SKIP_TESTS=true ./hotfix.sh
```

## Покрытие кода

Текущее покрытие кода можно посмотреть после запуска тестов:

```bash
# HTML отчет
open htmlcov/index.html

# Терминальный вывод
pytest --cov=da --cov-report=term-missing
```

## Написание новых тестов

### Структура теста

```python
def test_feature_name(client, app):
    """Описание теста."""
    # Arrange (подготовка)
    with app.app_context():
        # Создание тестовых данных
        pass
    
    # Act (действие)
    response = client.get("/route/")
    
    # Assert (проверка)
    assert response.status_code == 200
    assert b"expected content" in response.data
```

### Фикстуры

Доступные фикстуры из `conftest.py`:

- `app` - Flask приложение
- `client` - тестовый клиент Flask
- `runner` - CLI runner
- `seed_basics` - базовые данные (локации, типы устройств, склады)
- `super_admin_user` - пользователь с ролью супер-администратора
- `admin_user` - пользователь с ролью администратора
- `regular_user` - обычный пользователь
- `logged_in_super_admin` - авторизованный супер-администратор
- `logged_in_admin` - авторизованный администратор
- `logged_in_user` - авторизованный обычный пользователь

### Примеры

#### Тест создания ресурса

```python
def test_create_resource_by_admin(logged_in_admin, app):
    """Администратор может создавать ресурсы."""
    response = logged_in_admin.post(
        "/resource/create",
        data={"name": "Test Resource"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    
    with app.app_context():
        resource = Resource.query.filter_by(name="Test Resource").first()
        assert resource is not None
```

#### Тест проверки прав доступа

```python
def test_delete_requires_super_admin(logged_in_admin, app):
    """Удаление требует прав супер-администратора."""
    with app.app_context():
        resource = Resource(name="Test")
        db.session.add(resource)
        db.session.commit()
        resource_id = resource.id
    
    response = logged_in_admin.post(f"/resource/{resource_id}/delete")
    assert response.status_code == 403
```

## CI/CD интеграция

Для интеграции с CI/CD системами (GitHub Actions, GitLab CI и т.д.) используйте:

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=da --cov-report=xml
```

## Лучшие практики

1. **Каждый новый функционал должен иметь тесты** - добавьте тесты в соответствующий файл
2. **Тесты должны быть независимыми** - каждый тест должен работать автономно
3. **Используйте фикстуры** - не дублируйте код создания тестовых данных
4. **Проверяйте граничные случаи** - дубликаты, отсутствующие данные, неверные права доступа
5. **Тестируйте все роли** - USER, ADMIN, SUPER_ADMIN должны быть покрыты тестами

## Отчеты

После запуска тестов создаются отчеты:

- `htmlcov/index.html` - HTML отчет о покрытии кода
- `htmlcov/` - детальные отчеты по модулям
- Терминальный вывод с результатами тестов

## Устранение неполадок

### Тесты не запускаются

```bash
# Проверьте установку зависимостей
pip install -r requirements.txt

# Проверьте виртуальное окружение
which python
source venv/bin/activate
```

### Тесты падают

```bash
# Запуск с подробным выводом
pytest -v --tb=long

# Запуск конкретного теста
pytest tests/test_auth.py::test_registration_and_login_flow -v
```

### Проблемы с базой данных

Тесты используют in-memory SQLite базу данных, которая создается и удаляется автоматически. Если возникают проблемы:

```bash
# Очистка кэша pytest
pytest --cache-clear
```




