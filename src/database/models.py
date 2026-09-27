from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, func, Table
from sqlalchemy.orm import relationship, mapped_column, Mapped, DeclarativeBase
from sqlalchemy.sql.schema import ForeignKey, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.sql.sqltypes import Date


class Base(DeclarativeBase):
    pass

class Contact(Base):
    __tablename__ = "Contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    birthday: Mapped[datetime] = mapped_column(Date, nullable=False)
    additional_data: Mapped[str] = mapped_column(String(255), nullable=True)
    user_id = Column(
        "user_id",
        ForeignKey("Users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user = relationship("User", backref="contacts")

class User(Base):
    __tablename__ = "Users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar: Mapped[str] = mapped_column(String(255), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)