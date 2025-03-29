from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import create_engine, Engine
from sqlmodel import Session, SQLModel
from redis.asyncio import Redis, ConnectionPool

from hse_hw3_ap_url_shortener.settings.config import ConfigDep


def get_engine(config: ConfigDep) -> Engine:
    return create_engine(config.db_url)


EngineDep = Annotated[Engine, Depends(get_engine)]


def get_session(engine: EngineDep):
    with Session(engine) as session:
        yield session


def create_db_and_tables(engine: EngineDep):
    SQLModel.metadata.create_all(engine)


SessionDep = Annotated[Session, Depends(get_session)]


async def get_redis(config: ConfigDep) -> Redis:
    return Redis(
        connection_pool=ConnectionPool.from_url(config.redis_url, decode_responses=True)
    )


RedisDep = Annotated[Redis, Depends(get_redis)]
