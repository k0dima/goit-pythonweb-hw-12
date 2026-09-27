

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
    contact_services = ContactService(db)
    contacts = await contact_services.get_upcoming_birthdays(skip, limit, user)

    return contacts

@router.get("/{contact_id}", status_code=status.HTTP_200_OK)
async def read_contact(
        contact_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
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
    contact_services = ContactService(db)

    deleted_contact = await contact_services.delete_contact(contact_id, user)

    if not deleted_contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found"
        )

    return deleted_contact
