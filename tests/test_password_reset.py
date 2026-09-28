import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

from jose import jwt
from sqlalchemy import select

from src.conf.config import settings
from src.database.models import User
from src.services.auth import Hash, create_email_token, create_password_reset_token
from src.services.email import send_reset_password_email
from tests.conftest import TestingSessionLocal, test_user


def test_password_reset_request_does_not_reveal_account(client, monkeypatch, fake_redis):
    send_email = AsyncMock()
    monkeypatch.setattr("src.api.auth.send_reset_password_email", send_email)

    unknown = client.post(
        "/api/auth/reset-password", json={"email": "unknown@example.com"}
    )
    known = client.post(
        "/api/auth/reset-password", json={"email": test_user["email"]}
    )

    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()
    send_email.assert_awaited_once()
    assert send_email.await_args.args[0] == test_user["email"]
    assert len(fake_redis.values) == 1


def test_password_reset_changes_password_once(client, monkeypatch):
    send_email = AsyncMock()
    monkeypatch.setattr("src.api.auth.send_reset_password_email", send_email)
    new_password = "new-password-123"

    async def restore_password():
        async with TestingSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == test_user["email"])
            )
            user = result.scalar_one()
            user.hashed_password = Hash().get_password_hash(test_user["password"])
            await session.commit()

    try:
        prior_login = client.post(
            "/api/auth/login",
            data={"username": test_user["email"], "password": test_user["password"]},
        )
        assert prior_login.status_code == 200
        prior_access_token = prior_login.json()["access_token"]

        request = client.post(
            "/api/auth/reset-password", json={"email": test_user["email"]}
        )
        assert request.status_code == 200, request.text
        token = send_email.await_args.args[2]

        changed = client.post(
            "/api/auth/reset-password/confirm",
            json={"token": token, "password": new_password},
        )
        assert changed.status_code == 200, changed.text

        prior_session = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {prior_access_token}"},
        )
        assert prior_session.status_code == 401

        replay = client.post(
            "/api/auth/reset-password/confirm",
            json={"token": token, "password": "another-password"},
        )
        assert replay.status_code == 400

        old_login = client.post(
            "/api/auth/login",
            data={"username": test_user["email"], "password": test_user["password"]},
        )
        new_login = client.post(
            "/api/auth/login",
            data={"username": test_user["email"], "password": new_password},
        )
        assert old_login.status_code == 401
        assert new_login.status_code == 200
        new_session = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {new_login.json()['access_token']}"},
        )
        assert new_session.status_code == 200
    finally:
        asyncio.run(restore_password())


def test_verification_token_cannot_reset_password(client):
    token = create_email_token({"sub": test_user["email"], "type_token": "verified"})

    response = client.post(
        "/api/auth/reset-password/confirm",
        json={"token": token, "password": "new-password-123"},
    )

    assert response.status_code == 400


def test_reset_token_cannot_confirm_email(client):
    token, _ = create_password_reset_token(test_user["email"])

    response = client.get(f"/api/auth/confirmed_email/{token}")

    assert response.status_code == 400


def test_verification_token_still_confirms_email(client):
    token = create_email_token({"sub": test_user["email"], "type_token": "verified"})

    response = client.get(f"/api/auth/confirmed_email/{token}")

    assert response.status_code == 200


def test_reset_email_uses_reset_template(monkeypatch):
    mailer = Mock()
    mailer.send_message = AsyncMock()
    monkeypatch.setattr("src.services.email.FastMail", Mock(return_value=mailer))

    asyncio.run(
        send_reset_password_email(test_user["email"], "http://testserver/", "token")
    )

    assert mailer.send_message.await_args.kwargs["template_name"] == "reset_password_email.html"


def test_expired_password_reset_token_is_rejected(client):
    token = jwt.encode(
        {
            "sub": test_user["email"],
            "type_token": "reset-password",
            "jti": "expired-token",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = client.post(
        "/api/auth/reset-password/confirm",
        json={"token": token, "password": "new-password-123"},
    )

    assert response.status_code == 422
