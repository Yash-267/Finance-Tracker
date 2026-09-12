from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    type: Literal["income", "expense"]
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    category: str = Field(min_length=1)

class RecurringTransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    type: Literal["income", "expense"]
    category: str = Field(min_length=1)
    description: str
    frequency: Literal["daily", "monthly", "weekly", "yearly"]
    start_date: datetime