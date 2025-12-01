#!/bin/bash

echo "🚀 Перенос кода в GitLab"
echo "========================"
echo ""
echo "Новый репозиторий: https://code.dev-ittest.ru/ittest/device-accounting/da-python"
echo ""

# Проверка текущего remote
echo "📋 Текущие remotes:"
git remote -v
echo ""

# Добавление GitLab remote (если еще нет)
if ! git remote | grep -q gitlab; then
    echo "➕ Добавление GitLab remote..."
    git remote add gitlab https://code.dev-ittest.ru/ittest/device-accounting/da-python.git
    echo "✅ GitLab remote добавлен"
else
    echo "✅ GitLab remote уже существует"
fi

echo ""
echo "📤 Отправка кода в GitLab..."
echo ""
echo "⚠️  Вам потребуется:"
echo "   1. Логин от GitLab"
echo "   2. Токен доступа (Personal Access Token) с правами write_repository"
echo ""
echo "   Создать токен: https://code.dev-ittest.ru/-/user_settings/personal_access_tokens"
echo ""

# Попытка отправки
git push gitlab main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Код успешно перенесен в GitLab!"
    echo ""
    echo "📝 Следующие шаги:"
    echo "   1. Проверьте: https://code.dev-ittest.ru/ittest/device-accounting/da-python"
    echo "   2. Сделайте GitHub репозиторий приватным (там были пароли в истории)"
    echo ""
else
    echo ""
    echo "❌ Ошибка при отправке"
    echo ""
    echo "💡 Попробуйте:"
    echo "   1. Использовать SSH: git remote set-url gitlab git@code.dev-ittest.ru:ittest/device-accounting/da-python.git"
    echo "   2. Или использовать токен доступа (см. MIGRATE_TO_GITLAB.md)"
    echo ""
fi
