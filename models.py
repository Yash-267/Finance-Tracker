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
    role: Mapped[str] = mapped_column(String(20), default="user")
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

class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key= True, index=True)
    name: Mapped[str] = mapped_column(String(225))
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class GroupExpense(Base):
    __tablename__ = "group_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), index=True)
    paid_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(225))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ExpenseShare(Base):
    __tablename__ = "expense_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_expense_id: Mapped[int] = mapped_column(Integer, ForeignKey("group_expenses.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    share_amount: Mapped[float] = mapped_column(Float)

class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), index=True)
    paid_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))   # who is repaying
    paid_to: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))   # who receives the repayment
    amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(225))
    monthly_limit: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BudgetAlert(Base):
    __tablename__ = "budget_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    budget_id: Mapped[int] = mapped_column(Integer, ForeignKey("budgets.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    threshold: Mapped[str] = mapped_column(String(20))  # "approaching" or "exceeded"
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(String(225))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)