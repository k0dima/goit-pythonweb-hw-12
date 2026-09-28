from typing import Sequence

from sqlalchemy import or_,and_, select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schema import CreateContact, UpdateContact
from datetime import date, timedelta


# 3. CRUD API
# На придачу до базового функціоналу CRUD API також повинен мати наступні функції:
# Контакти повинні бути доступні для пошуку за іменем, прізвищем чи адресою електронної пошти (Query параметри).
# API повинен мати змогу отримати список контактів з днями народження на найближчі 7 днів.

def like_escape(value: str) -> str:
    """Escape SQL LIKE wildcard characters in a search term.

    Args:
        value (str): Untrusted search text.

    Returns:
        str: Text with backslashes, percent signs, and underscores escaped.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

class ContactRepository:
    """Query and persist contacts belonging to a specific user."""

    def __init__(self, session: AsyncSession):
        """Store the database session used by repository methods.

        Args:
            session (AsyncSession): Database session.
        """
        self.db = session  


    async def get_all_contacts(self, skip: int, limit: int, user: User, query: str | None = None):
        """List a user's contacts with optional case-insensitive search.

        Args:
            skip (int): Number of matching contacts to skip.
            limit (int): Maximum number of contacts to return.
            user (User): Owner whose identifier filters the query.
            query (str | None): Search term for first name, last name, or email.

        Returns:
            list[Contact]: Matching contacts.
        """
        where = []
        if query:
            pattern = f"%{like_escape(query)}%"
            where.append(
                or_(
                    Contact.first_name.ilike(pattern, escape="\\"),
                    Contact.last_name.ilike(pattern, escape="\\"),
                    Contact.email.ilike(pattern, escape="\\"),
                )
            )

        stmt = (
            select(Contact)
            .filter_by(user_id=user.id)
            .where(*where)
            .offset(skip)
            .limit(limit)     
        )
        result = await self.db.execute(stmt)

        return result.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Find one contact owned by the given user.

        Args:
            contact_id (int): Contact identifier.
            user (User): Contact owner.

        Returns:
            Contact | None: Matching contact, if present.
        """
        stmt = (
            select(Contact)
            .filter_by(user_id=user.id)
            .where(Contact.id == contact_id)
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def create_contact(self, body: CreateContact, user: User):
        """Create and persist a contact for the given user.

        Args:
            body (CreateContact): Contact fields to store.
            user (User): Contact owner.

        Returns:
            Contact: Created and refreshed contact.
        """
        contact = Contact(**body.model_dump(), user_id=user.id)

        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)

        return contact
        

    async def update_contact(self, contact_id: int,  body: UpdateContact, user: User):
        """Update supplied fields of a contact owned by the user.

        Args:
            contact_id (int): Contact identifier.
            body (UpdateContact): Fields supplied for the update.
            user (User): Contact owner.

        Returns:
            Contact | None: Updated contact, if present.
        """
        contact =  await self.get_contact_by_id(contact_id, user)

        if contact is None:
            return None

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(contact, field, value)

        await self.db.commit()
        await self.db.refresh(contact)

        return contact

    async def delete_contact(self, contact_id: int, user: User):
        """Delete a contact owned by the given user.

        Args:
            contact_id (int): Contact identifier.
            user (User): Contact owner.

        Returns:
            Contact | None: Deleted contact, if present.
        """
        contact =  await self.get_contact_by_id(contact_id, user)

        if contact is None:
            return None

        await self.db.delete(contact)
        await self.db.commit()

        return contact

    async def get_upcoming_birthdays(self, skip: int, limit: int, user: User) -> Sequence[Contact]:
        """Find the user's contacts with birthdays from today through day seven.

        Args:
            skip (int): Number of matching contacts to skip.
            limit (int): Maximum number of contacts to return.
            user (User): Contact owner.

        Returns:
            Sequence[Contact]: Contacts with birthdays in the requested window.
        """
        today = date.today()

        conditions = [
            and_(
                extract("month", Contact.birthday) == (today + timedelta(days=offset)).month,
                extract("day", Contact.birthday) == (today + timedelta(days=offset)).day,
            )
            for offset in range(8)
        ]

        stmt = (
            select(Contact)
            .filter_by(user_id=user.id)
            .where(or_(*conditions))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)

        return result.scalars().all()
