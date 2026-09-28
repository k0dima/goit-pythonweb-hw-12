import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects import postgresql

import re
from datetime import date

from src.database.models import User, Contact
from src.schema import CreateContact, UpdateContact
from src.repository.contacts import ContactRepository


@pytest.fixture
def mock_session():
    mock_session = AsyncMock(spec=AsyncSession)
    return mock_session


@pytest.fixture
def contact_repository(mock_session):
    return ContactRepository(mock_session)


@pytest.fixture
def user():
    return User(id=1, email="test_user")


@pytest.mark.asyncio
async def test_get_all_contacts(
    mock_session,
    contact_repository: ContactRepository,
    user,
):
    contacts = [
        Contact(
            id=1,
            first_name="test_user",
            last_name="test_user",
            email="test_user@test.com",
            phone="1234567890",
            birthday=date(1990, 1, 1),
            user=user,
        )]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = contacts
    mock_session.execute.return_value = mock_result

    result = await contact_repository.get_all_contacts(0, 10, user)

    assert result == contacts
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_contact_by_id(
    mock_session, contact_repository: ContactRepository, user
):
    contact = Contact(
        id=10,
        first_name="Test",
        last_name="Contact",
        email="contact@example.com",
        phone="1234567890",
        birthday=date(1990, 1, 1),
        user=user,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = contact
    mock_session.execute.return_value = mock_result

    result = await contact_repository.get_contact_by_id(contact.id, user)

    assert result is contact
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_contact_by_id_not_found(
    mock_session, contact_repository: ContactRepository, user
):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await contact_repository.get_contact_by_id(9999, user)

    assert result is None
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_contact(
    mock_session, contact_repository: ContactRepository, user
):
    body = CreateContact(
        first_name="Test",
        last_name="Contact",
        email="contact@example.com",
        phone="1234567890",
        birthday=date(1990, 1, 1),
        additional_data="Test note",
    )

    result = await contact_repository.create_contact(body, user)

    assert isinstance(result, Contact)
    for field, expected in body.model_dump().items():
        assert getattr(result, field) == expected

    assert result.user_id == user.id
    mock_session.add.assert_called_once_with(result)
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_update_contact(
    mock_session, contact_repository: ContactRepository, user
):
    contact = Contact(
        id=10,
        first_name="Old",
        last_name="Contact",
        email="contact@example.com",
        phone="1234567890",
        birthday=date(1990, 1, 1),
        additional_data="Keep this note",
        user=user,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = contact
    mock_session.execute.return_value = mock_result

    body = UpdateContact(first_name="New")

    result = await contact_repository.update_contact(contact.id, body, user)

    assert result is contact
    assert result.first_name == "New"
    assert result.last_name == "Contact"
    assert result.email == "contact@example.com"
    assert result.phone == "1234567890"
    assert result.birthday == date(1990, 1, 1)
    assert result.additional_data == "Keep this note"
    assert result.user is user

    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(contact)


@pytest.mark.asyncio
async def test_update_contact_not_found(
    mock_session, contact_repository: ContactRepository, user
):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    body = UpdateContact(first_name="New")

    result = await contact_repository.update_contact(9999, body, user)

    assert result is None
    mock_session.commit.assert_not_awaited()
    mock_session.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_contact(
    mock_session, contact_repository: ContactRepository, user
):
    contact = Contact(
        id=10,
        first_name="Test",
        last_name="Contact",
        email="contact@example.com",
        phone="1234567890",
        birthday=date(1990, 1, 1),
        user=user,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = contact
    mock_session.execute.return_value = mock_result

    result = await contact_repository.delete_contact(contact.id, user)

    assert result is contact
    mock_session.delete.assert_awaited_once_with(contact)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_contact_not_found(
    mock_session, contact_repository: ContactRepository, user
):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await contact_repository.delete_contact(9999, user)

    assert result is None
    mock_session.delete.assert_not_awaited()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_upcoming_birthdays(
    mock_session,
    contact_repository: ContactRepository,
    user,
    monkeypatch,
):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 28)

    monkeypatch.setattr("src.repository.contacts.date", FixedDate)

    contacts = [
        Contact(
            id=10,
            first_name="Test",
            last_name="Contact",
            email="contact@example.com",
            phone="1234567890",
            birthday=date(1990, 1, 3),
            user=user,
        )
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = contacts
    mock_session.execute.return_value = mock_result

    result = await contact_repository.get_upcoming_birthdays(0, 10, user)

    assert result == contacts
    mock_session.execute.assert_awaited_once()

    statement = mock_session.execute.await_args.args[0]
    sql = str(statement.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))

    pairs = re.findall(
        r"EXTRACT\(month FROM [^)]+\) = (\d+) AND "
        r"EXTRACT\(day FROM [^)]+\) = (\d+)",
        sql,
    )
    assert [(int(month), int(day)) for month, day in pairs] == [
        (12, 28),
        (12, 29),
        (12, 30),
        (12, 31),
        (1, 1),
        (1, 2),
        (1, 3),
        (1, 4),
    ]