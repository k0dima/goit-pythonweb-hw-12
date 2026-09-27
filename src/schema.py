from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, EmailStr


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

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class RequestEmail(BaseModel):
    email: EmailStr
