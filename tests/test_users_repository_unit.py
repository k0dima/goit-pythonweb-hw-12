import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.schema import UserCreate
from src.repository.users import UserRepository


@pytest.fixture
def mock_session():
    mock_session = AsyncMock(spec=AsyncSession)
    return mock_session


@pytest.fixture
def user_repository(mock_session):
    return UserRepository(mock_session)


@pytest.mark.asyncio
async def test_get_user_by_id(
        mock_session, user_repository: UserRepository
):
    user = User(
        id=1001,
        email="test_user@test.com",
        hashed_password="test description",
        avatar="https://example.com/avatar.jpg",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = mock_result

    result = await user_repository.get_user_by_id(user_id=user.id)

    assert result is user
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_email(
        mock_session, user_repository: UserRepository
):
    user = User(
        id=1001,
        email="test_user@test.com",
        hashed_password="test description",
        avatar="https://example.com/avatar.jpg",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = mock_result

    result = await user_repository.get_user_by_email(user.email)

    assert result is user
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user(
        mock_session,
        user_repository: UserRepository
):
    avatar = "https://example.com/avatar.jpg"
    body = UserCreate(
        email="test_user@test.com",
        password="already_hashed_password",
    )

    result = await user_repository.create_user(
        body,
        avatar=avatar
    )

    assert isinstance(result, User)
    assert result.email == body.email
    assert result.hashed_password == body.password
    assert result.avatar == avatar

    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)

@pytest.mark.asyncio
async def test_confirmed_email(
    mock_session, user_repository: UserRepository
):
    user = User(
        id=1001,
        email="test_user@test.com",
        confirmed=False,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = mock_result

    await user_repository.confirmed_email(user.email)

    assert user.confirmed is True
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_avatar_url(
    mock_session, user_repository: UserRepository
):
    user = User(
        id=1001,
        email="test_user@test.com",
        avatar="https://example.com/old.jpg",
    )
    new_avatar = "https://example.com/new.jpg"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute.return_value = mock_result

    result = await user_repository.update_avatar_url(
        user.email, new_avatar
    )

    assert result is user
    assert result.avatar == new_avatar
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(user)