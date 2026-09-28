

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.schema import CreateContact, UpdateContact
from src.services.contacts import ContactService
from src.database.db import get_db
from src.database.models import User
from src.services.auth import get_current_user

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("/", status_code=status.HTTP_200_OK)
async def read_contacts(
        skip: int = 0,
        limit: int = 100,
        query: str | None = None,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    """List the current user's contacts, optionally filtered by a search term.

    Args:
        skip (int): Number of matching contacts to skip.
        limit (int): Maximum number of contacts to return.
        query (str | None): Search term for first name, last name, or email.
        db (AsyncSession): Database session.
        user (User): Authenticated contact owner.

    Returns:
        list[Contact]: Matching contacts belonging to the current user.
    """
    contact_services = ContactService(db)
    contacts = await contact_services.find_contacts(skip, limit, user, query)

    return contacts

@router.get("/upcoming-birthdays", status_code=status.HTTP_200_OK)
async def read_upcoming_birthdays(
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    """List the user's contacts with birthdays in the next seven days.

    Args:
        skip (int): Number of matching contacts to skip.
        limit (int): Maximum number of contacts to return.
        db (AsyncSession): Database session.
        user (User): Authenticated contact owner.

    Returns:
        list[Contact]: Contacts whose birthdays fall between today and day seven.
    """
    contact_services = ContactService(db)
    contacts = await contact_services.get_upcoming_birthdays(skip, limit, user)

    return contacts

@router.get("/{contact_id}", status_code=status.HTTP_200_OK)
async def read_contact(
        contact_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Get one contact belonging to the current user.

    Args:
        contact_id (int): Contact identifier.
        db (AsyncSession): Database session.
        user (User): Authenticated contact owner.

    Returns:
        Contact: The requested contact.

    Raises:
        HTTPException: If the contact is missing or belongs to another user (404).
    """
    contact_services = ContactService(db)
    contact = await contact_services.get_contact(contact_id, user)

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )

    return contact

@router.post("/", status_code=status.HTTP_201_CREATED )
async def create_contact(
    body: CreateContact,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a contact owned by the current user.

    Args:
        body (CreateContact): Contact fields supplied by the client.
        db (AsyncSession): Database session.
        user (User): Authenticated contact owner.

    Returns:
        Contact: The newly created contact.

    Raises:
        HTTPException: If the contact email already exists (409).
    """
    try:
        contact_services = ContactService(db)

        return await contact_services.create(body, user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this email already exists"
        )


@router.put("/{contact_id}", status_code=status.HTTP_200_OK)
async def update_contact(
        contact_id: int,
        body: UpdateContact,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Update fields of a contact belonging to the current user.

    Args:
        contact_id (int): Contact identifier.
        body (UpdateContact): Fields to change.
        db (AsyncSession): Database session.
        user (User): Authenticated contact owner.

    Returns:
        Contact: The updated contact.

    Raises:
        HTTPException: If the contact is missing or inaccessible (404), or its
            new email conflicts with an existing contact (409).
    """
    contact_services = ContactService(db)

    try:
        updated_contact = await contact_services.update_contact(contact_id, body, user)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact with this email already exists",
        )

    if not updated_contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )

    return updated_contact


@router.delete("/{contact_id}")
async def delete_contact(
        contact_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """Delete a contact belonging to the current user.

    Args:
        contact_id (int): Contact identifier.
        db (AsyncSession): Database session.
        user (User): Authenticated contact owner.

    Returns:
        Contact: The deleted contact.

    Raises:
        HTTPException: If the contact is missing or inaccessible (404).
    """
    contact_services = ContactService(db)

    deleted_contact = await contact_services.delete_contact(contact_id, user)

    if not deleted_contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )

    return deleted_contact
