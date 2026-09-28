from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from src.roles import UserRole

class CreateContact(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    birthday: date
    additional_data: str | None = None

class UpdateContact(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    birthday: date | None = None
    additional_data: str | None = None

class User(BaseModel):
    id: int
    email: EmailStr
    avatar: str | None
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class RequestEmail(BaseModel):
    email: EmailStr

class ConfirmPassword(BaseModel):
    token: str
    password: str = Field(min_length=8)
