import secrets
import string
from datetime import datetime
from typing import Annotated
from typing import Optional, List
from urllib.parse import quote

from fastapi import Depends
from fastapi import HTTPException, status
from pydantic import HttpUrl
from redis.asyncio import Redis
from sqlmodel import select, Session

from hse_hw3_ap_url_shortener.db import RedisDep
from hse_hw3_ap_url_shortener.model.dbmodel import Link, User
from hse_hw3_ap_url_shortener.settings.config import Config
from hse_hw3_ap_url_shortener.settings.config import ConfigDep


def _generate_random_string(length: int) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class LinkService:
    def __init__(self, config: Config, redis: Redis):
        self.config = config
        self.redis = redis

    async def create_link(
        self,
        session: Session,
        user: User,
        original_url: HttpUrl,
        custom_alias: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Link:
        original_url = quote(original_url.unicode_string(), safe="%/:=&?~#+!$,;'@()*[]")

        if custom_alias:
            existing_link = await self.get_link_by_short_code(session, custom_alias)
            if existing_link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Custom alias already exists",
                )
            short_code = custom_alias
        else:
            short_code = await self.generate_unique_short_code(session)

        link = Link(
            short_code=short_code,
            original_url=original_url,
            user_id=user.id,
            expires_at=expires_at,
        )
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    async def generate_unique_short_code(
        self, session: Session, length: int = 6
    ) -> str:
        while True:
            short_code = _generate_random_string(length)
            print("Try code", short_code)
            existing = await self.get_link_by_short_code(session, short_code)
            if not existing:
                return short_code

    async def get_link_by_short_code(
        self, session: Session, short_code: str
    ) -> Optional[Link]:
        cached = await self.redis.get(f"link:{short_code}")
        if cached:
            return Link.model_validate_json(cached)
        return session.exec(select(Link).where(Link.short_code == short_code)).first()

    async def delete_link(self, session: Session, user: User, short_code: str) -> None:
        link = await self.get_link_by_short_code(session, short_code)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
            )
        if link.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You dont have access to that link",
            )
        await self.batch_delete([link], session)

    async def batch_delete(self, links: List[Link], session: Session):
        await self.redis.delete(*[f"link:{link.short_code}" for link in links])
        for link in links:
            session.delete(link)
        session.commit()

    async def update_link(
        self,
        session: Session,
        user: User,
        short_code: str,
        new_url: str,
    ) -> Link:
        link = await self.get_link_by_short_code(session, short_code)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link not found",
            )
        if link.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You dont have access to that link",
            )
        await self.redis.delete(f"link:{short_code}")
        link.original_url = new_url
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    def update_visit(self, session: Session, link: Link) -> None:
        link.visits += 1
        link.last_visit = datetime.now()
        session.add(link)
        session.commit()

    async def get_stats(self, session: Session, short_code: str) -> Link:
        link = await self.get_link_by_short_code(session, short_code)
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
            )
        return link

    def search_by_original_url(
        self, session: Session, user: User, original_url: str
    ) -> List[Link]:
        return list(
            session.exec(
                select(Link).where(
                    (Link.original_url == original_url) & (Link.user_id == user.id)
                )
            ).all()
        )


def get_service(config: ConfigDep, redis: RedisDep) -> LinkService:
    return LinkService(config=config, redis=redis)


LinkServiceDep = Annotated[LinkService, Depends(get_service)]
