"""Вспомогательные функции для запросов к базе данных."""
from sqlalchemy.orm import Query


def filter_not_deleted(query: Query, model) -> Query:
    """
    Фильтрует запрос, исключая удаленные записи.
    
    Args:
        query: SQLAlchemy query объект
        model: Модель с полем deleted_at
    
    Returns:
        Query: Отфильтрованный запрос
    """
    return query.filter(model.deleted_at.is_(None))


def get_active_entities(model, order_by=None):
    """
    Получает все активные (не удаленные) сущности.
    
    Args:
        model: SQLAlchemy модель
        order_by: Поле для сортировки (опционально)
    
    Returns:
        Query: Запрос с активными сущностями
    """
    query = model.query.filter(model.deleted_at.is_(None))
    if order_by:
        query = query.order_by(order_by)
    return query


def get_deleted_entities(model, order_by=None):
    """
    Получает все удаленные сущности.
    
    Args:
        model: SQLAlchemy модель
        order_by: Поле для сортировки (опционально)
    
    Returns:
        Query: Запрос с удаленными сущностями
    """
    query = model.query.filter(model.deleted_at.isnot(None))
    if order_by:
        query = query.order_by(order_by)
    return query

