import logging
from datetime import datetime
from typing import Annotated

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends
from sqlalchemy import Engine
from sqlmodel import select, Session

from hse_hw3_ap_url_shortener.db import EngineDep
from hse_hw3_ap_url_shortener.model.dbmodel import Link
from hse_hw3_ap_url_shortener.service.link import LinkService, LinkServiceDep
from hse_hw3_ap_url_shortener.settings.config import Config, ConfigDep

logger = logging.getLogger(__name__)


class CleanupService:
    def __init__(self, config: Config, engine: Engine, link_service: LinkService):
        self.scheduler = AsyncIOScheduler()
        self.config = config
        self.engine = engine
        self.link_service = link_service

    async def delete_expired_links(self):
        with Session(self.engine) as session:
            expired_links = session.exec(
                select(Link).where(Link.expires_at < datetime.now())
            ).all()
            logging.info("Expiring links: %s", expired_links)
            if len(expired_links) > 0:
                await self.link_service.batch_delete(expired_links, session)
                session.commit()

    def start_scheduler(self):
        self.scheduler.add_job(
            self.delete_expired_links,
            "interval",
            minutes=self.config.cleanup_interval_minutes,
            next_run_time=datetime.now(),
        )
        self.scheduler.start()


_service = None


def get_service(
    config: ConfigDep, engine: EngineDep, link_service: LinkServiceDep
) -> CleanupService:
    global _service
    if not _service:
        _service = CleanupService(
            config=config, engine=engine, link_service=link_service
        )
    return _service


CleanupServiceDep = Annotated[CleanupService, Depends(get_service)]
