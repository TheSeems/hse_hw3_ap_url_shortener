from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from freezegun import freeze_time
from httpx import Response

from hse_hw3_ap_url_shortener.main import app
from hse_hw3_ap_url_shortener.model.model import LinkCreateIn, LinkUpdateIn

client = TestClient(app)


def create_test_link(token: str, custom_alias: str = None) -> Response:
    request = LinkCreateIn(
        original_url="https://example.com",
        custom_alias=custom_alias,
        expires_at=datetime.now() + timedelta(days=1),
    ).model_dump()
    request["expires_at"] = str(request["expires_at"])
    return client.post(
        "/links/shorten", json=request, headers={"Authorization": f"Bearer {token}"}
    )


# Tests
def test_create_short_link_success(authorized_token):
    response = create_test_link(authorized_token)

    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com"
    assert data["expires_at"] is not None


def test_create_duplicate_alias(authorized_token):
    create_test_link(authorized_token, "mylink")
    response = create_test_link(authorized_token, "mylink")

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_expired_link(authorized_token):
    request = LinkCreateIn(
        original_url="https://example.com",
        expires_at=datetime.now() - timedelta(minutes=1),
    ).model_dump()
    request["expires_at"] = str(request["expires_at"])
    response = client.post(
        "/links/shorten",
        json=request,
        headers={"Authorization": f"Bearer {authorized_token}"},
    )

    assert response.status_code == 400
    assert "future" in response.json()["detail"]


def test_redirect_success(authorized_token):
    link = create_test_link(authorized_token).json()

    response = client.get(f"/links/{link['short_code']}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com"


def test_redirect_expired_link(authorized_token):
    request = LinkCreateIn(
        original_url="https://example.com",
        expires_at=datetime.now() + timedelta(hours=1),
    ).model_dump()
    request["expires_at"] = str(request["expires_at"])

    response = client.post(
        "/links/shorten",
        json=request,
        headers={"Authorization": f"Bearer {authorized_token}"},
    )
    short_code = response.json()["short_code"]

    with freeze_time(datetime.max):
        response = client.get(f"/links/{short_code}", follow_redirects=False)

    assert response.status_code == 410


def test_delete_link_success(authorized_token):
    link = create_test_link(authorized_token).json()

    response = client.delete(
        f"/links/{link['short_code']}",
        headers={"Authorization": f"Bearer {authorized_token}"},
    )
    assert response.status_code == 204

    # Verify deletion
    stats_response = client.get(f"/links/{link['short_code']}/stats")
    assert stats_response.status_code == 404


def test_delete_unauthorized(authorized_token):
    # Create first user
    link = create_test_link(authorized_token).json()

    # Create second user
    client.post(
        "/auth/register",
        json={
            "name": "testuser2",
            "email": "test2@example.com",
            "password": "testpass",
        },
    )
    token2 = client.post(
        "/auth/login", json={"email": "test2@example.com", "password": "testpass"}
    ).json()["token"]

    # Try to delete with second user
    response = client.delete(
        f"/links/{link['short_code']}", headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 403


def test_update_link_success(authorized_token):
    link = create_test_link(authorized_token).json()

    response = client.put(
        f"/links/{link['short_code']}",
        json=LinkUpdateIn(original_url="https://updated.com").model_dump(),
        headers={"Authorization": f"Bearer {authorized_token}"},
    )

    assert response.status_code == 200
    assert response.json()["original_url"] == "https://updated.com"


def test_get_stats(authorized_token):
    link = create_test_link(authorized_token).json()

    # Access link to generate stats
    client.get(f"/links/{link['short_code']}")

    response = client.get(f"/links/{link['short_code']}/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["visits"] == 1
    assert stats["last_visit"] is not None


def test_search_links(authorized_token):
    create_test_link(authorized_token)

    response = client.get(
        "/links/search",
        params={"original_url": "https://example.com"},
        headers={"Authorization": f"Bearer {authorized_token}"},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    assert all(link["original_url"] == "https://example.com" for link in results)


def test_invalid_short_code():
    response = client.get("/links/invalid_link")
    assert response.status_code == 404
