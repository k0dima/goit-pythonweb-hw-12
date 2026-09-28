from sqlalchemy.ext.asyncio import AsyncSession
from libgravatar import Gravatar

from src.repository.users import UserRepository
from src.schema import UserCreate


class UserService:
    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate):
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(e)

        return await self.repository.create_user(body, avatar)

    async def get_user_by_id(self, user_id: int):
        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_email(self, email: str):
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str):
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        return await self.repository.update_avatar_url(email, url)

    async def update_password(self, user_id: int, hashed_password: str):
        return await self.repository.update_user_hash_password(user_id, hashed_password)
