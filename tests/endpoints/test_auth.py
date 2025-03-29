from hse_hw3_ap_url_shortener.model.model import UserCreateIn, UserLoginIn


def test_register_success(test_client):
    response = test_client.post(
        "/auth/register",
        json=UserCreateIn(
            name="sample",
            email="sample@a.nl",
            password="test123",
        ).model_dump(),
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "sample",
        "email": "sample@a.nl",
    }


def test_register_incorrect_email(test_client):
    response = test_client.post(
        "/auth/register",
        json=dict(
            name="sample",
            email="sample",
            password="test123",
        ),
    )
    assert response.status_code == 422
    assert "An email address must have an @-sign" in response.text


def test_login_success(test_client):
    test_register_success(test_client)
    response = test_client.post(
        "/auth/login",
        json=UserLoginIn(
            email="sample@a.nl",
            password="test123",
        ).model_dump(),
    )
    assert response.status_code == 200
    result = response.json()
    assert "token" in result
    assert result["token_type"] == "bearer"


def test_login_incorrect_credentials(test_client):
    response = test_client.post(
        "/auth/login",
        json=UserLoginIn(
            email="sample@a.nl",
            password="test1234",
        ).model_dump(),
    )
    assert response.status_code == 401


def test_login_incorrect_data(test_client):
    response = test_client.post(
        "/auth/login",
        json=dict(
            email="sample",
            password="test1234",
        ),
    )
    assert response.status_code == 422


def test_whoami_authenticated(test_client, authorized_token):
    response = test_client.get(
        "/auth/whoami", headers={"Authorization": f"Bearer {authorized_token}"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["email"] == "sample@a.nl"
    assert result["name"] == "sample"


def test_whoami_unauthenticated(test_client):
    assert test_client.get("/auth/whoami").status_code == 401


def test_whoami_incorrect_token(test_client):
    assert (
        test_client.get(
            "/auth/whoami", headers={"Authorization": "Bearer stub"}
        ).status_code
        == 401
    )
