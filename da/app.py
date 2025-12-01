import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь для импортов
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from da import create_app
except ImportError:
    # Fallback для прямого запуска
    from . import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)