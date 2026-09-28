from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.schema import UserCreate


class UserRepository:
    """Persist and retrieve user accounts with an async database session."""

    def __init__(self, session: AsyncSession):
        """Store the database session used by repository methods.

        Args:
            session (AsyncSession): Database session.
        """
        self.db = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Find a user by primary key.

        Args:
            user_id (int): User identifier.

        Returns:
            User | None: Matching user, if present.
        """
        stmt = select(User).filter_by(id=user_id)
        user = await self.db.execute(stmt)

        return user.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Find a user by email address.

        Args:
            email (str): User email address.

        Returns:
            User | None: Matching user, if present.
        """
        stmt = select(User).filter_by(email=email)
        user = await self.db.execute(stmt)

        return user.scalar_one_or_none()

    async def create_user(self, body: UserCreate, avatar: str | None) -> User:
        """Persist a new user with a hashed password and optional avatar.

        Args:
            body (UserCreate): Email and already-hashed password.
            avatar (str | None): Initial avatar URL, if available.

        Returns:
            User: Created and refreshed database user.
        """
        user = User(
            **body.model_dump(exclude_unset=True, exclude={"password"}),
            hashed_password=body.password,
            avatar=avatar
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def confirmed_email(self, email: str) -> None:
        """Mark an existing user's email as confirmed.

        Args:
            email (str): Email address of the user to confirm.
        """
        user = await self.get_user_by_email(email)
        user.confirmed = True
        await self.db.commit()

    async def update_avatar_url(self, email: str, url: str) -> User | None:
        """Update the avatar URL of an existing user.

        Args:
            email (str): User email address.
            url (str): New avatar URL.

        Returns:
            User: Updated and refreshed database user.
        """
        user = await self.get_user_by_email(email)
        user.avatar = url
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user_hash_password(self, user_id: int, hashed_password: str) -> User | None:
        """Store a new password hash for a user.

        Args:
            user_id (int): User identifier.
            hashed_password (str): New password hash.

        Returns:
            User | None: Updated user, if present.
        """
        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        user.hashed_password = hashed_password
        await self.db.commit()
        await self.db.refresh(user)
        return user
