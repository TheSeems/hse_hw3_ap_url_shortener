from functools import lru_cache
from pathlib import Path
from typing import Annotated
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi import Depends

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config(BaseSettings):
    db_user: str
    db_password: str
    db_url: str

    redis_host: str
    redis_port: int

    secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    algo: str = "HS256"
    access_token_expire_minutes: int = 30

    cleanup_interval_minutes: int = 60

    top_links_cache_size: int = 10
    cache_ttl_hours: int = 24
    populate_cache_interval_minutes: int = 60

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env")


@lru_cache()
def get_config() -> Config:
    return Config()  # type: ignore


ConfigDep = Annotated[Config, Depends(get_config)]
