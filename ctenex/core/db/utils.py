from typing import Type

from sqlalchemy.inspection import inspect

from ctenex.core.db.base import AbstractBase


def get_entity_values(entity: AbstractBase) -> dict:
    return {c.key: getattr(entity, c.key) for c in inspect(entity).mapper.column_attrs}


def get_entity_fields(entity: Type[AbstractBase]) -> list[str]:
    return [c.key for c in inspect(entity).mapper.column_attrs]
