from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

import sqlalchemy.exc
from pydantic import BaseModel
from sqlalchemy import select, insert, update, delete
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession

from db import Base


class Repository:

    def get(self, *args, **kwargs):
        raise NotImplementedError

    def filter(self, *args, **kwargs):
        raise NotImplementedError

    def create(self, *args, **kwargs):
        raise NotImplementedError

    def update(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        raise NotImplementedError


ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class RepositoryInterface(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self._model = model

    async def get(self, session: AsyncSession, id: int) -> Optional[ModelType]:
        statement = select(self._model).where(self._model.id == id)
        result = await session.execute(statement)
        await session.commit()
        return result.scalar_one_or_none()

    async def filter(self, session: AsyncSession, *, offset: int = 0, limit: int = 100, **kwargs) -> List[ModelType]:
        statement = select(self._model)
        for key, value in kwargs.items():
            statement = statement.where(getattr(self._model, key) == value)
        statement = statement.offset(offset).limit(limit)
        result = await session.execute(statement)
        await session.commit()
        return result.scalars().all()

    async def create(self, session: AsyncSession, *, data: CreateSchemaType) -> ModelType:
        statement = insert(self._model).values(**data.dict()).returning(self._model)
        try:
            result = await session.execute(statement)
        except sqlalchemy.exc.IntegrityError:
            await session.rollback()
            return None
        await session.commit()
        return result.scalar_one()

    async def update(self, session: AsyncSession, *, model_id: int,
                     data: Union[UpdateSchemaType, Dict[str, Any]]) -> Optional[ModelType]:
        statement = update(self._model).where(self._model.id == model_id) \
                                       .values(**data.dict()) \
                                       .returning(self._model)
        try:
            result = await session.execute(statement)
            user = result.scalar_one()
        except sqlalchemy.exc.NoResultFound:
            await session.rollback()
            return None
        await session.commit()
        return user

    async def delete(self, session: AsyncSession, *, model_id: int) -> None:
        statement = delete(self._model).where(self._model.id == model_id) \
                                       .returning(self._model)
        result = await session.execute(statement)
        user = result.scalar_one()
        await session.commit()
        return user
