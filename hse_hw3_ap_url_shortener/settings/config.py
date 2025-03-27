from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config(BaseSettings):
    db_url: str

    redis_url: str

    secret_key: str
    algo: str
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
