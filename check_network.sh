#!/bin/bash

echo "🔍 Проверка сетевых настроек..."

echo ""
echo "1. Проверка UFW:"
sudo ufw status | grep 2022

echo ""
echo "2. Проверка iptables (если доступен):"
if command -v iptables &> /dev/null; then
    echo "   iptables доступен"
    sudo iptables -L -n | grep 2022 || echo "   Правил для порта 2022 в iptables не найдено"
else
    echo "   iptables не установлен"
fi

echo ""
echo "3. Проверка прослушивания портов:"
sudo ss -tlnp | grep 2022

echo ""
echo "4. Проверка внешнего IP:"
curl -s ifconfig.me || curl -s icanhazip.com || echo "Не удалось определить внешний IP"

echo ""
echo "5. Информация о сетевых интерфейсах:"
ip addr show | grep -E "inet |inet6 " | head -5

echo ""
echo "📝 Если порт не открыт на уровне провайдера, нужно:"
echo "   - AWS: открыть в Security Groups"
echo "   - Azure: открыть в Network Security Groups"
echo "   - Google Cloud: открыть в Firewall Rules"
echo "   - Другие провайдеры: проверить настройки firewall/security groups"




