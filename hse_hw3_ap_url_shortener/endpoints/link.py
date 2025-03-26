import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from hse_hw3_ap_url_shortener.db import SessionDep
from hse_hw3_ap_url_shortener.model.model import (
    LinkCreateIn,
    LinkCreateOut,
    LinkUpdateIn,
    LinkStatsOut,
)
from hse_hw3_ap_url_shortener.service.auth import CurrentUserDep
from hse_hw3_ap_url_shortener.service.link import LinkServiceDep

links_router = APIRouter()

logger = logging.getLogger(__name__)


@links_router.post(
    "/links/shorten", response_model=LinkCreateOut, status_code=status.HTTP_201_CREATED
)
async def create_short_link(
    link_in: LinkCreateIn,
    current_user: CurrentUserDep,
    link_service: LinkServiceDep,
    session: SessionDep,
):
    if link_in.expires_at and link_in.expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expires_at must be in the future",
        )
    link = await link_service.create_link(
        session=session,
        user=current_user,
        original_url=link_in.original_url,
        custom_alias=link_in.custom_alias,
        expires_at=link_in.expires_at,
    )
    return LinkCreateOut(
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


@links_router.get("/links/search", response_model=List[LinkStatsOut])
async def search_links_by_url(
    original_url: str,
    current_user: CurrentUserDep,
    link_service: LinkServiceDep,
    session: SessionDep,
):
    links = link_service.search_by_original_url(session, current_user, original_url)
    return [
        LinkStatsOut(
            short_code=link.short_code,
            original_url=link.original_url,
            created_at=link.created_at,
            visits=link.visits,
            last_visit=link.last_visit,
            expires_at=link.expires_at,
        )
        for link in links
    ]


@links_router.get("/links/{short_code}")
async def redirect_to_original(
    short_code: str,
    link_service: LinkServiceDep,
    session: SessionDep,
):
    link = await link_service.get_link_by_short_code(session, short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        )

    if link.expires_at and link.expires_at < datetime.now():
        session.delete(link)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This link is expired",
        )

    link_service.update_visit(session, link)
    return RedirectResponse(url=link.original_url)


@links_router.delete("/links/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_short_link(
    short_code: str,
    current_user: CurrentUserDep,
    link_service: LinkServiceDep,
    session: SessionDep,
):
    await link_service.delete_link(session, current_user, short_code)


@links_router.put("/links/{short_code}", response_model=LinkCreateOut)
async def update_short_link(
    short_code: str,
    link_update: LinkUpdateIn,
    current_user: CurrentUserDep,
    link_service: LinkServiceDep,
    session: SessionDep,
):
    link = await link_service.update_link(
        session=session,
        user=current_user,
        short_code=short_code,
        new_url=link_update.original_url,
    )
    return LinkCreateOut(
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


@links_router.get("/links/{short_code}/stats", response_model=LinkStatsOut)
async def get_link_statistics(
    short_code: str,
    link_service: LinkServiceDep,
    session: SessionDep,
):
    link = await link_service.get_stats(session, short_code)
    return LinkStatsOut(
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        visits=link.visits,
        last_visit=link.last_visit,
        expires_at=link.expires_at,
    )
