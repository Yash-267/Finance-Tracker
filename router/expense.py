from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select,func

from database import get_db
from models import Transaction, User
from schemas import TransactionCreate
from security import get_current_user

from datetime import datetime, timezone
from calendar import monthrange

router = APIRouter(prefix="/transactions", tags=["Expenses"])

#add transaction
@router.post("/add")
def create_transaction(
    transaction:TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_transaction = Transaction(
        amount=transaction.amount,
        type=transaction.type,
        description=transaction.description,
        created_at=transaction.created_at,
        category=transaction.category,
        user_id=current_user.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return {"message": "Transaction added successfully", "transaction_id": new_transaction.id}

#get all transactions
@router.get("/all")
def get_all_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.execute(select(Transaction).where(Transaction.user_id == current_user.id)).scalars().all()
    return transactions

#delete transaction
@router.delete("/delete/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transaction = db.execute(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == current_user.id)).scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(transaction)
    db.commit()
    return {"message": "Transaction deleted successfully"}

#Monthly income-expense summary
@router.get("/analytics/monthly")
def monthly_summary(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    start_date = datetime(year,month,1)
    last_day = monthrange(year,month)[1]
    end_date = datetime(year,month,last_day,23,59,59)

    income = db.scalar(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "income",
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        )
    )

    expense = db.scalar(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        )
    )

    total_income = income or 0
    total_expense = expense or 0

    monthly_balance = total_income - total_expense

    return{
        "month": month,
        "year": year,
        "total_income": total_income,
        "total_expense": total_expense,
        "monthly_balance": monthly_balance
    } 

#Category-wise expense summary
@router.get("/analytics/category")
def category_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    results= db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("total_amount")).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense"
        ).group_by(Transaction.category)
    ).all()

    return{
        "category_summary": {
            category: float(total_amount) 
            for category, total_amount in results
        }
    }

#Top 3 expense categories
@router.get("/analytics/top-categories")
def top_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    results = db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("total_amount")).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense"
        ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).limit(3)
    ).all()

    if not results:
        return {"message": "No expense transactions found."}

    return {
        "top_categories": [
            {"category": category, "total_amount": float(total_amount)}
            for category, total_amount in results
        ]
    }