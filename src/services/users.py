from sqlalchemy.ext.asyncio import AsyncSession
from libgravatar import Gravatar

from src.repository.users import UserRepository
from src.schema import UserCreate


class UserService:
    """Coordinate user account operations for API routes."""

    def __init__(self, db: AsyncSession):
        """Create a user service using the given database session.

        Args:
            db (AsyncSession): Database session for user operations.
        """
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate):
        """Create a user with a Gravatar URL when one can be obtained.

        Args:
            body (UserCreate): Email and already-hashed password.

        Returns:
            User: Created database user.
        """
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(e)

        return await self.repository.create_user(body, avatar)

    async def get_user_by_id(self, user_id: int):
        """Find a user by database identifier.

        Args:
            user_id (int): User identifier.

        Returns:
            User | None: Matching user, if present.
        """
        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_email(self, email: str):
        """Find a user by email address.

        Args:
            email (str): User email address.

        Returns:
            User | None: Matching user, if present.
        """
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str):
        """Mark an existing user's email address as confirmed.

        Args:
            email (str): Email address to confirm.
        """
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        """Save a new avatar URL for an existing user.

        Args:
            email (str): User email address.
            url (str): Public URL of the uploaded avatar.

        Returns:
            User: Updated database user.
        """
        return await self.repository.update_avatar_url(email, url)

    async def update_password(self, user_id: int, hashed_password: str):
        """Replace a user's password hash.

        Args:
            user_id (int): User identifier.
            hashed_password (str): New password hash.

        Returns:
            User | None: Updated user, if present.
        """
        return await self.repository.update_user_hash_password(user_id, hashed_password)
