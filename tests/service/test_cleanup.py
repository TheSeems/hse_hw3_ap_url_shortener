from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from hse_hw3_ap_url_shortener.model.dbmodel import Link
from hse_hw3_ap_url_shortener.service.cleanup import CleanupService
from hse_hw3_ap_url_shortener.service.link import LinkService


def create_test_links(engine, created_user, expired_count=1, valid_count=1):
    with Session(engine) as session:
        for i in range(expired_count):
            session.add(
                Link(
                    short_code=f"expired{i}",
                    original_url=f"https://expired{i}.com",
                    expires_at=datetime.now() - timedelta(days=1),
                    user_id=created_user,
                )
            )

        for i in range(valid_count):
            session.add(
                Link(
                    short_code=f"valid{i}",
                    original_url=f"https://valid{i}.com",
                    expires_at=datetime.now() + timedelta(days=1),
                    user_id=created_user,
                )
            )

        session.commit()


@pytest.mark.asyncio
async def test_deletes_expired_links(test_config, created_user, temp_db, mock_redis):
    create_test_links(temp_db, created_user, expired_count=2, valid_count=1)
    service = CleanupService(test_config, temp_db, LinkService(test_config, mock_redis))

    await service.delete_expired_links()

    with Session(temp_db) as session:
        links = session.exec(select(Link)).all()
        assert len(links) == 1
        assert all(link.short_code.startswith("valid") for link in links)


@pytest.mark.asyncio
async def test_removes_redis_entries(test_config, created_user, temp_db, mock_redis):
    create_test_links(temp_db, created_user)
    link_service = LinkService(test_config, mock_redis)

    with Session(temp_db) as session:
        expired_link = session.exec(select(Link)).first()
        await mock_redis.setex(f"link:{expired_link.short_code}", 3600, "data")

    service = CleanupService(test_config, temp_db, link_service)

    await service.delete_expired_links()

    assert "link:expired0" not in mock_redis.data


@pytest.mark.asyncio
async def test_handles_no_expired_links(test_config, created_user, temp_db, mock_redis):
    create_test_links(temp_db, created_user, expired_count=0, valid_count=3)
    service = CleanupService(test_config, temp_db, LinkService(test_config, mock_redis))

    await service.delete_expired_links()

    with Session(temp_db) as session:
        assert len(session.exec(select(Link)).all()) == 3


@pytest.mark.asyncio
async def test_scheduler_configuration(test_config, temp_db, mock_redis):
    test_config.cleanup_interval_minutes = 30
    service = CleanupService(test_config, temp_db, LinkService(test_config, mock_redis))

    service.start_scheduler()

    assert len(service.scheduler.get_jobs()) == 1
    job = service.scheduler.get_jobs()[0]
    assert job.trigger.interval.total_seconds() == 30 * 60


@pytest.mark.asyncio
async def test_batch_deletion(test_config, created_user, temp_db, mock_redis):
    create_test_links(temp_db, created_user, expired_count=5, valid_count=0)
    link_service = LinkService(test_config, mock_redis)
    service = CleanupService(test_config, temp_db, link_service)

    await service.delete_expired_links()

    with Session(temp_db) as session:
        assert len(session.exec(select(Link)).all()) == 0
    assert len(mock_redis.data) == 0


@pytest.mark.asyncio
async def test_partial_expiration(test_config, created_user, temp_db, mock_redis):
    with Session(temp_db) as session:
        session.add(
            Link(
                short_code="partial1",
                original_url="https://partial1.com",
                expires_at=datetime.now() - timedelta(minutes=5),
                user_id=created_user,
            )
        )
        session.add(
            Link(
                short_code="partial2",
                original_url="https://partial2.com",
                expires_at=datetime.now() + timedelta(minutes=5),
                user_id=created_user,
            )
        )
        session.commit()

    service = CleanupService(test_config, temp_db, LinkService(test_config, mock_redis))

    await service.delete_expired_links()

    with Session(temp_db) as session:
        remaining = session.exec(select(Link)).all()
        assert len(remaining) == 1
        assert remaining[0].short_code == "partial2"
