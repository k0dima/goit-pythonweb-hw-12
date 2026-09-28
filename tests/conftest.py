import asyncio

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from main import app
from src.database.models import Base, User
from src.database.db import get_db
from src.services.auth import create_access_token, Hash
from src.services.redis_client import get_redis

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

test_user = {
    "email": "deadpool@example.com",
    "password": "12345678",
}

class FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        if not isinstance(value, (str, bytes)):
            raise TypeError("Redis value must be a string or bytes")
        self.values[key] = value

    async def delete(self, key):
        return self.values.pop(key, None)


@pytest.fixture(autouse=True)
def fake_redis():
    cache = FakeRedis()
    app.dependency_overrides[get_redis] = lambda: cache
    try:
        yield cache
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.fixture(scope="module", autouse=True)
def init_models_wrap():
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as session:
            hash_password = Hash().get_password_hash(test_user["password"])
            current_user = User(
                email=test_user["email"],
                hashed_password=hash_password,
                confirmed=True,
                avatar="https://twitter.com/gravatar",
            )
            session.add(current_user)

            await session.commit()

    asyncio.run(init_models())


@pytest.fixture(scope="module")
def client():
    # Dependency override

    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception as err:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture()
async def get_token():
    token = await create_access_token(data={"sub": test_user["email"]})
    return token
