import logging
from typing import Tuple, List, Optional

from ..extensions import db
from ..models import User, UserRole
from ..services.delete_handler import handle_entity_deletion

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def get_all_users() -> List[User]:
        """Возвращает список всех пользователей, отсортированных по дате создания."""
        return User.query.order_by(User.created_at.desc()).all()

    @staticmethod
    def set_user_role(user_id: int, new_role_value: str) -> Tuple[bool, str]:
        """Изменяет роль пользователя."""
        user = db.session.get(User, user_id)
        if not user:
            return False, "Пользователь не найден"

        if not new_role_value or new_role_value not in [r.value for r in UserRole]:
            return False, "Неверная роль"

        old_role = user.role
        try:
            user.role = UserRole(new_role_value)
            db.session.commit()
            logger.info("Роль пользователя %s изменена с %s на %s", user.email, old_role.value, new_role_value)
            return True, f"Роль пользователя {user.full_name} изменена с {old_role.value} на {new_role_value}"
        except Exception as e:
            db.session.rollback()
            logger.exception("Ошибка при изменении роли пользователя %s", user_id)
            return False, f"Ошибка при изменении роли: {str(e)}"

    @staticmethod
    def delete_user(user_id: int, current_user: User) -> Tuple[bool, str]:
        """
        Удаляет пользователя с проверкой прав.
        current_user: пользователь, инициирующий удаление.
        """
        user = db.session.get(User, user_id)
        if not user:
            return False, "Пользователь не найден"

        # Нельзя удалить самого себя
        if user.id == current_user.id:
            return False, "Нельзя удалить самого себя"

        # Супер-админ может удалить любого, админ - только обычных пользователей
        # (проверка прав доступа к самому методу удаления делается в route через декоратор,
        # но здесь проверяем бизнес-правило: кого именно может удалить админ)
        if not current_user.is_super_admin and user.is_admin:
            return False, "Админы не могут удалять других админов и супер-админов"

        user_email = user.email
        user_name = user.full_name
        
        # Используем общий обработчик удаления
        success, message = handle_entity_deletion(user, "user", user_name)
        
        if success:
             logger.info("Пользователь %s удален пользователем %s", user_email, current_user.email)
             
        return success, message

