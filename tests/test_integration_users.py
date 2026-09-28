import asyncio
import pytest
from unittest.mock import patch
from sqlalchemy import update

from src.database.models import User as DbUser
from src.roles import UserRole
from tests.conftest import TestingSessionLocal, test_user


def test_get_me(client, get_token):
    token = get_token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("api/users/me", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["role"] == UserRole.USER.value
    assert "avatar" in data


@pytest.fixture
def admin_role():
    async def set_role(role: UserRole):
        async with TestingSessionLocal() as session:
            await session.execute(
                update(DbUser)
                .where(DbUser.email == test_user["email"])
                .values(role=role.value)
            )
            await session.commit()

    asyncio.run(set_role(UserRole.ADMIN))
    try:
        yield
    finally:
        asyncio.run(set_role(UserRole.USER))


@patch("src.services.upload_file.UploadFileService.upload_file")
def test_update_avatar_user(
        mock_upload_file,
        client,
        admin_role,
        get_token
):
    fake_url = "http://example.com/avatar.jpg"
    mock_upload_file.return_value = fake_url

    headers = {"Authorization": f"Bearer {get_token}"}

    file_data = {"file": ("avatar.jpg", b"fake image content", "image/jpeg")}

    response = client.patch("/api/users/avatar", headers=headers, files=file_data)

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["avatar"] == fake_url

    mock_upload_file.assert_called_once()


@patch("src.services.upload_file.UploadFileService.upload_file")
def test_update_avatar_forbidden_for_user(
        mock_upload_file,
        client,
        get_token
):
    fake_url = "http://example.com/avatar.jpg"
    mock_upload_file.return_value = fake_url

    headers = {"Authorization": f"Bearer {get_token}"}

    file_data = {"file": ("avatar.jpg", b"fake image content", "image/jpeg")}

    response = client.patch("/api/users/avatar", headers=headers, files=file_data)

    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "Administrator access required"
    mock_upload_file.assert_not_called()
