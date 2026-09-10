from pydantic import BaseModel,Field
from typing import Optional,Literal

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
    description: str | None = None
    date: str  
    category: str = Field(min_length=1)