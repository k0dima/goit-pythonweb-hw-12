from sqlalchemy.ext.asyncio import AsyncSession

from src.schema import CreateContact, UpdateContact
from src.repository.contacts import ContactRepository
from src.database.models import User

class ContactService:
    """Coordinate contact operations for the API."""

    def __init__(self, db: AsyncSession):
        """Create a contact service using the given database session.

        Args:
            db (AsyncSession): Database session for contact operations.
        """
        self.contacts = ContactRepository(db)

    async def create(self, contact: CreateContact, user: User):
        """Create a contact owned by the current user.

        Args:
            contact (CreateContact): Contact data to store.
            user (User): Contact owner.

        Returns:
            Contact: Created contact.
        """
        return await self.contacts.create_contact(contact, user)

    async def find_contacts(self, skip: int, limit: int, user: User, query: str | None = None):
        """List a user's contacts with optional search and pagination.

        Args:
            skip (int): Number of matching contacts to skip.
            limit (int): Maximum number of contacts to return.
            user (User): Contact owner.
            query (str | None): Optional name or email search term.

        Returns:
            list[Contact]: Matching contacts.
        """
        return await self.contacts.get_all_contacts(skip, limit, user, query)

    async def get_contact(self, contact_id: int, user: User):
        """Find one of the user's contacts by identifier.

        Args:
            contact_id (int): Contact identifier.
            user (User): Contact owner.

        Returns:
            Contact | None: Matching contact, if present.
        """
        return await self.contacts.get_contact_by_id(contact_id, user)

    async def update_contact(self, contact_id: int, body: UpdateContact, user: User):
        """Apply supplied changes to one of the user's contacts.

        Args:
            contact_id (int): Contact identifier.
            body (UpdateContact): Fields to update.
            user (User): Contact owner.

        Returns:
            Contact | None: Updated contact, if present.
        """
        return await self.contacts.update_contact(contact_id, body, user)

    async def delete_contact(self, contact_id: int, user: User):
        """Delete one of the user's contacts.

        Args:
            contact_id (int): Contact identifier.
            user (User): Contact owner.

        Returns:
            Contact | None: Deleted contact, if present.
        """
        return await self.contacts.delete_contact(contact_id, user)

    async def get_upcoming_birthdays(self, skip: int, limit: int, user: User):
        """List contacts whose birthdays fall within the next seven days.

        Args:
            skip (int): Number of matching contacts to skip.
            limit (int): Maximum number of contacts to return.
            user (User): Contact owner.

        Returns:
            list[Contact]: Contacts with upcoming birthdays.
        """
        return await self.contacts.get_upcoming_birthdays(skip, limit, user)
