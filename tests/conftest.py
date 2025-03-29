import os

import pytest
from sqlalchemy import create_engine
from starlette.testclient import TestClient

from hse_hw3_ap_url_shortener.db import get_engine, create_db_and_tables, get_redis
from hse_hw3_ap_url_shortener.main import app
from hse_hw3_ap_url_shortener.model.model import UserLoginIn
from hse_hw3_ap_url_shortener.settings.config import Config, PROJECT_ROOT
from tests.endpoints.test_auth import test_register_success
from tests.mock.redis import MockRedis


@pytest.fixture(scope="session", autouse=True)
def test_config() -> Config:
    Config.model_config.update(env_file=PROJECT_ROOT / "../.test.env")
    return Config()


@pytest.fixture(scope="function", autouse=True)
def temp_db(tmp_path_factory):
    path = (
        tmp_path_factory.mktemp("hse_hw3_ap_url_shortener_test")
        / "hse_hw3_ap_url_shortener_test.db"
    )
    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    create_db_and_tables(engine)
    app.dependency_overrides[get_engine] = lambda: engine
    yield engine
    os.remove(path)


@pytest.fixture(scope="function", autouse=True)
def mock_redis():
    redis = MockRedis()
    app.dependency_overrides[get_redis] = lambda: redis
    yield redis
    del app.dependency_overrides[get_redis]


@pytest.fixture(scope="session", autouse=True)
def test_client():
    return TestClient(app)


@pytest.fixture(scope="function")
def authorized_token(test_client, created_user):
    response = test_client.post(
        "/auth/login",
        json=UserLoginIn(
            email="sample@a.nl",
            password="test123",
        ).model_dump(),
    )
    assert response.status_code == 200
    result = response.json()
    return result["token"]


@pytest.fixture(scope="function")
def created_user(test_client):
    test_register_success(test_client)
    return 1
