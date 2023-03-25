from typing import Generic, Type, TypeVar, Union, Sequence
from uuid import UUID

import sqlalchemy.exc
from pydantic import BaseModel
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db import Base
from utils.exceptions import ObjectAlreadyExists, ObjectDoesNotExist


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

    async def get(self, session: AsyncSession, id: Union[int, UUID]) -> ModelType:
        statement = select(self._model).where(self._model.id == id)
        result = await session.execute(statement)
        if (obj := result.scalar_one_or_none()) is None:
            await session.rollback()
            raise ObjectDoesNotExist
        await session.commit()
        return obj

    async def filter(self, session: AsyncSession, *, offset: int = 0,
                     limit: int = 100, **options) -> Sequence[ModelType]:
        statement = select(self._model).filter_by(**options) \
                                       .offset(offset) \
                                       .limit(limit)
        result = await session.execute(statement)
        await session.commit()
        return result.scalars().all()

    async def create(self, session: AsyncSession, *, schema: CreateSchemaType) -> ModelType:
        statement = insert(self._model).values(schema.dict()) \
                                       .returning(self._model)
        try:
            result = await session.execute(statement)
        except sqlalchemy.exc.IntegrityError:
            await session.rollback()
            raise ObjectAlreadyExists
        await session.commit()
        return result.scalar_one()
    
    async def bulk_create(self, session: AsyncSession, *,
                          schema: Sequence[CreateSchemaType]) -> Sequence[ModelType]:
        statement = insert(self._model).values([row.dict() for row in schema]) \
                                       .returning(self._model)
        try:
            result = await session.execute(statement)
        except sqlalchemy.exc.IntegrityError:
            await session.rollback()
            raise ObjectAlreadyExists
        await session.commit()
        return result.scalars().all()
    
    async def update(self, session: AsyncSession, id: Union[int, UUID], *,
                     schema: UpdateSchemaType) -> ModelType:
        statement = update(self._model).where(self._model.id == id) \
                                       .values(**schema.dict()) \
                                       .returning(self._model)
        result = await session.execute(statement)
        if (obj := result.scalar_one_or_none()) is None:
            await session.rollback()
            raise ObjectDoesNotExist
        await session.commit()
        return obj

    async def delete(self, session: AsyncSession, *, id: Union[int, UUID]) -> ModelType:
        statement = delete(self._model).where(self._model.id == id) \
                                       .returning(self._model)
        result = await session.execute(statement)
        if (obj := result.scalar_one_or_none()) is None:
            await session.rollback()
            raise ObjectDoesNotExist
        await session.commit()
        return obj
