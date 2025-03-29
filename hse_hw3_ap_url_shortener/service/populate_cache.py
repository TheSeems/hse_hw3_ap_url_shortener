import logging
from datetime import datetime, timedelta
from typing import Annotated, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy import Engine
from sqlmodel import select, Session

from hse_hw3_ap_url_shortener.db import RedisDep, EngineDep
from hse_hw3_ap_url_shortener.model.dbmodel import Link
from hse_hw3_ap_url_shortener.settings.config import Config, ConfigDep

logger = logging.getLogger(__name__)


class PopulateCacheService:
    def __init__(self, config: Config, redis: Redis, engine: Engine):
        self.scheduler = AsyncIOScheduler()
        self.config = config
        self.redis = redis
        self.engine = engine

    def _get_top_links(self) -> List[Link]:
        with Session(self.engine) as session:
            result = session.exec(
                select(Link)
                .order_by(Link.visits.desc())  # type: ignore
                .limit(self.config.top_links_cache_size)
            )
            return list(result.all())

    async def populate_cache(self):
        top_links = self._get_top_links()
        logger.info("About to populate cache with links %s", top_links)

        all_keys = [f"link:{link.short_code}" for link in top_links]

        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.delete(*all_keys)
            for link in top_links:
                await pipe.setex(
                    f"link:{link.short_code}",
                    timedelta(hours=self.config.cache_ttl_hours),
                    link.model_dump_json(),
                )
            await pipe.execute()

    def start_scheduler(self):
        self.scheduler.add_job(
            self.populate_cache,
            "interval",
            minutes=self.config.populate_cache_interval_minutes,
            next_run_time=datetime.now(),
        )
        self.scheduler.start()


_service = None


def get_service(
    config: ConfigDep, redis: RedisDep, engine: EngineDep
) -> PopulateCacheService:
    global _service
    if not _service:
        _service = PopulateCacheService(config=config, redis=redis, engine=engine)
    return _service


PopulateCacheServiceDep = Annotated[PopulateCacheService, Depends(get_service)]
