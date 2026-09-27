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
    """Escape LIKE wildcards -- an unescaped % in a search matches every row."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

class ContactRepository:
    def __init__(self, session: AsyncSession):
        self.db = session  


    async def get_all_contacts(self, skip: int, limit: int, user: User, query: str | None = None):
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
            .filter_by(user=user)
            .where(*where)
            .offset(skip)
            .limit(limit)     
        )
        result = await self.db.execute(stmt)

        return result.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        stmt = (
            select(Contact)
            .filter_by(user=user)
            .where(Contact.id == contact_id)
        )

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def create_contact(self, body: CreateContact, user: User):
        contact = Contact(**body.model_dump(), user=user)

        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)

        return contact
        

    async def update_contact(self, contact_id: int,  body: UpdateContact, user: User):
        contact =  await self.get_contact_by_id(contact_id, user)

        if contact is None:
            return None

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(contact, field, value)

        await self.db.commit()
        await self.db.refresh(contact)

        return contact

    async def delete_contact(self, contact_id: int, user: User):
        contact =  await self.get_contact_by_id(contact_id, user)

        if contact is None:
            return None

        await self.db.delete(contact)
        await self.db.commit()

        return contact

    async def get_upcoming_birthdays(self, skip: int, limit: int, user: User) -> Sequence[Contact]:
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
            .filter_by(user=user)
            .where(or_(*conditions))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)

        return result.scalars().all()