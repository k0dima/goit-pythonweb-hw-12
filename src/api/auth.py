from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from time import time

from src.schema import UserCreate, Token, User, RequestEmail, ConfirmPassword
from src.services.auth import (
    create_access_token,
    create_password_reset_token,
    get_data_from_token,
    PASSWORD_RESET_TTL_SECONDS,
    TypeToken,
    Hash,
)
from src.services.users import UserService
from src.services.email import send_email, send_reset_password_email
from src.database.db import get_db
from src.conf.config import settings
from src.services.redis_client import get_redis
from redis.asyncio import Redis

router = APIRouter(prefix="/auth", tags=["auth"])


# Реєстрація користувача
@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
        user_data: UserCreate,
        background_tasks: BackgroundTasks,
        request: Request,
        db: AsyncSession = Depends(get_db),
):
    """Register a user and schedule an email verification message.

    Args:
        user_data (UserCreate): Email address and plain-text password.
        background_tasks (BackgroundTasks): Runs email sending after the response.
        request (Request): Provides the base URL for the verification link.
        db (AsyncSession): Database session.

    Returns:
        User: The created user. FastAPI serializes it with the response model.

    Raises:
        HTTPException: If the email address is already registered (409).
    """
    user_service = UserService(db)

    email_user = await user_service.get_user_by_email(user_data.email)
    if email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким email вже існує",
        )

    user_data.password = Hash().get_password_hash(user_data.password)
    new_user = await user_service.create_user(user_data)
    background_tasks.add_task(
        send_email, new_user.email, str(request.base_url)
    )
    return new_user


# Логін користувача
@router.post("/login", response_model=Token)
async def login_user(
        form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """Authenticate a confirmed user and issue an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): Email in the username field and password.
        db (AsyncSession): Database session used to find the user.

    Returns:
        dict[str, str]: Access token and bearer token type.

    Raises:
        HTTPException: If the credentials are invalid or email is unconfirmed (401).
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(form_data.username)  # username is only `email`
    if not user or not Hash().verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email is not confirmed",
        )
    access_token = await create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """Confirm a user's email address using a verification token.

    Args:
        token (str): Signed email verification token.
        db (AsyncSession): Database session used to find and update the user.

    Returns:
        dict[str, str]: Message indicating whether the email was already confirmed.

    Raises:
        HTTPException: If the token is invalid or expired (422), has the wrong
            purpose (400), or its user cannot be found (400).
    """
    token_data = await get_data_from_token(token)
    email = token_data["sub"]
    type_token = token_data["type_token"]

    if type_token != TypeToken.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wrong token type",
        )

    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await user_service.confirmed_email(email)
    return {"message": "Email is verified"}


@router.post("/request_email")
async def request_email(
        body: RequestEmail,
        background_tasks: BackgroundTasks,
        request: Request,
        db: AsyncSession = Depends(get_db),
):
    """Schedule another verification email for an unconfirmed user.

    Args:
        body (RequestEmail): Email address to verify.
        background_tasks (BackgroundTasks): Sends the email after the response.
        request (Request): Provides the base URL for the verification link.
        db (AsyncSession): Database session used to find the user.

    Returns:
        dict[str, str]: Verification instructions or an already-confirmed message.

    Raises:
        HTTPException: If the email does not belong to a user (400).
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )

    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(
            send_email, user.email, str(request.base_url)
        )

    return {"message": "Check your email for verification"}


@router.post("/reset-password")
async def reset_password(
        body: RequestEmail,
        background_tasks: BackgroundTasks,
        request: Request,
        db: AsyncSession = Depends(get_db),
        cache: Redis = Depends(get_redis),
):
    """Request a one-time password reset token by email.

    Args:
        body (RequestEmail): Email address of the account to reset.
        background_tasks (BackgroundTasks): Sends the reset email after the response.
        request (Request): Provides the base URL for the documentation link.
        db (AsyncSession): Database session used to find the account.
        cache (Redis): Stores the token identifier until it expires.

    Returns:
        dict[str, str]: Message describing the next step in password recovery.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user and user.confirmed:
        token, token_id = create_password_reset_token(user.email)
        await cache.set(
            f"password-reset:{token_id}",
            user.email,
            ex=PASSWORD_RESET_TTL_SECONDS,
        )
        background_tasks.add_task(
            send_reset_password_email, user.email, str(request.base_url), token
        )
    return {"message": "If the account exists, check your email for password reset instructions"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(
        body: ConfirmPassword,
        db: AsyncSession = Depends(get_db),
        cache: Redis = Depends(get_redis),
):
    """Set a new password using a valid, unused reset token.

    Args:
        body (ConfirmPassword): Reset token and new plain-text password.
        db (AsyncSession): Database session used to update the password hash.
        cache (Redis): Consumes the token and revokes earlier access tokens.

    Returns:
        dict[str, str]: Confirmation that the password was changed.

    Raises:
        HTTPException: If the token is invalid or expired (422), has the wrong
            purpose (400), was already used (400), or the user is missing (400).
    """
    token_data = await get_data_from_token(body.token)
    email = token_data["sub"]
    type_token = token_data["type_token"]
    token_id = token_data.get("jti")

    if type_token != TypeToken.RESET_PASSWORD.value or not token_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )

    if await cache.getdel(f"password-reset:{token_id}") != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token",
        )

    user_data = await user_service.update_password(
        user.id,
        Hash().get_password_hash(body.password)
    )

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password failed to change"
        )


    await cache.set(
        f"auth:invalid-before:{email}",
        str(time()),
        ex=settings.JWT_EXPIRATION_SECONDS + 60,
    )
    await cache.delete(f"user:email:{email}")
    return {"message": "Password is successfully changed"}
