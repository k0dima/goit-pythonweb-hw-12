from sqlalchemy.ext.asyncio import AsyncSession

from src.schema import CreateContact, UpdateContact
from src.repository.contacts import ContactRepository
from src.database.models import User

class ContactService:
    def __init__(self, db: AsyncSession):
        self.contacts = ContactRepository(db)

    async def create(self, contact: CreateContact, user: User):
        return await self.contacts.create_contact(contact, user)

    async def find_contacts(self, skip: int, limit: int, user: User, query: str | None = None):
        return await self.contacts.get_all_contacts(skip, limit, user, query)

    async def get_contact(self, contact_id: int, user: User):
        return await self.contacts.get_contact_by_id(contact_id, user)

    async def update_contact(self, contact_id: int, body: UpdateContact, user: User):
        return await self.contacts.update_contact(contact_id, body, user)

    async def delete_contact(self, contact_id: int, user: User):
        return await self.contacts.delete_contact(contact_id, user)

    async def get_upcoming_birthdays(self, skip: int, limit: int, user: User):
        return await self.contacts.get_upcoming_birthdays(skip, limit, user)
