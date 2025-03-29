from datetime import datetime

import pytest
from sqlmodel import Session

from hse_hw3_ap_url_shortener.model.dbmodel import Link
from hse_hw3_ap_url_shortener.service.populate_cache import PopulateCacheService


def create_test_links(engine, created_user):
    with Session(engine) as session:
        links = [
            Link(
                short_code="most",
                original_url="https://most.com",
                visits=10,
                user_id=created_user,
            ),
            Link(
                short_code="middle",
                original_url="https://middle.com",
                visits=5,
                user_id=created_user,
            ),
            Link(
                short_code="least",
                original_url="https://least.com",
                visits=1,
                user_id=created_user,
            ),
        ]
        session.add_all(links)
        session.commit()


@pytest.mark.asyncio
async def test_populates_top_links(test_config, mock_redis, temp_db, created_user):
    test_config.top_links_cache_size = 2
    create_test_links(temp_db, created_user)
    service = PopulateCacheService(test_config, mock_redis, temp_db)
    await service.populate_cache()
    assert mock_redis.data["link:most"] is not None
    assert mock_redis.data["link:middle"] is not None
    assert "link:least" not in mock_redis.data


@pytest.mark.asyncio
async def test_respects_cache_size_limit(test_config, mock_redis, temp_db):
    test_config.top_links_cache_size = 2
    service = PopulateCacheService(test_config, mock_redis, temp_db)
    await service.populate_cache()
    assert len(mock_redis.data) == 0


@pytest.mark.asyncio
async def test_sets_correct_ttl(test_config, mock_redis, temp_db, created_user):
    test_config.top_links_cache_size = 2
    create_test_links(temp_db, created_user)
    service = PopulateCacheService(test_config, mock_redis, temp_db)
    test_start = datetime.now()
    await service.populate_cache()
    for code in ["most", "middle"]:
        key = f"link:{code}"
        expire_time = datetime.fromtimestamp(mock_redis.expires[key])
        expected_ttl = test_config.cache_ttl_hours * 3600
        assert (expire_time - test_start).total_seconds() == pytest.approx(
            expected_ttl, rel=1
        )


@pytest.mark.asyncio
async def test_clears_old_entries(test_config, mock_redis, temp_db, created_user):
    test_config.top_links_cache_size = 2
    service = PopulateCacheService(test_config, mock_redis, temp_db)

    with Session(temp_db) as session:
        links = [
            Link(
                short_code="old1",
                original_url="https://old1.com",
                visits=-1,
                user_id=created_user,
            ),
            Link(
                short_code="old2",
                original_url="https://old2.com",
                visits=-1,
                user_id=created_user,
            ),
        ]
        session.add_all(links)
        session.commit()

    create_test_links(temp_db, created_user)
    await service.populate_cache()

    assert "link:old1" not in mock_redis.data
    assert "link:old2" not in mock_redis.data


@pytest.mark.asyncio
async def test_scheduler_initialization(test_config, mock_redis, temp_db):
    test_config.populate_cache_interval_minutes = 10
    service = PopulateCacheService(test_config, mock_redis, temp_db)

    service.start_scheduler()

    assert len(service.scheduler.get_jobs()) == 1
    job = service.scheduler.get_jobs()[0]
    assert job.trigger.interval.total_seconds() == 10 * 60
