from datetime import datetime, timedelta, UTC
from enum import Enum
from secrets import token_urlsafe
from typing import Optional

from redis.asyncio import Redis
from src.services.redis_client import get_redis

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.database.db import get_db
from src.conf.config import settings
from src.services.users import UserService
from src.roles import UserRole
from src.database.models import User as UserDB
from src.schema import User as UserData


class Hash:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        return self.pwd_context.hash(password)


class TypeToken(str, Enum):
    VERIFIED = "verified"
    RESET_PASSWORD = "reset-password"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# define a function to generate a new access token
async def create_access_token(data: dict, expires_delta: Optional[int] = None):
    to_encode = data.copy()
    issued_at = datetime.now(UTC)
    if expires_delta:
        expire = issued_at + timedelta(seconds=expires_delta)
    else:
        expire = issued_at + timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
    to_encode.update({"iat": issued_at.timestamp(), "exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
        cache: Redis = Depends(get_redis),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email = payload["sub"]
        if email is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception

    revoked_at = await cache.get(f"auth:invalid-before:{email}")
    issued_at = payload.get("iat")
    if revoked_at is not None and (
        not isinstance(issued_at, (int, float)) or issued_at <= float(revoked_at)
    ):
        raise credentials_exception

    key = f"user:email:{email}"
    cached = await cache.get(key)

    if cached is not None:
        return UserData.model_validate_json(cached)

    db_user = await UserService(db).get_user_by_email(email)
    if db_user is None:
        raise credentials_exception

    current_user = UserData.model_validate(db_user)
    await cache.set(key, current_user.model_dump_json(), ex=600)
    return current_user


async def get_admin_user(
        user: UserDB = Depends(get_current_user),
) -> UserDB:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return user


def create_email_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=7)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return token


PASSWORD_RESET_TTL_SECONDS = 15 * 60


def create_password_reset_token(email: str) -> tuple[str, str]:
    token_id = token_urlsafe(32)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": email,
            "type_token": TypeToken.RESET_PASSWORD.value,
            "jti": token_id,
            "iat": now,
            "exp": now + timedelta(seconds=PASSWORD_RESET_TTL_SECONDS),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, token_id


async def get_data_from_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if not payload.get("exp") or not payload.get("sub") or not payload.get("type_token"):
            raise JWTError("Missing email token claims")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid or expired email token",
        )
