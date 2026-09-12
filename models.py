from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(225))
    email: Mapped[str] = mapped_column(String(225), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(225))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(225))
    category: Mapped[str] = mapped_column(String(225))
    description: Mapped[Optional[str]] = mapped_column(String(225), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(225))
    category: Mapped[str] = mapped_column(String(225))
    description: Mapped[str] = mapped_column(String(225))

    frequency: Mapped[str] = mapped_column(String(50))  # daily, weekly, monthly, yearly
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)