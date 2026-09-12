from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database import get_db
from models import Transaction, User, RecurringTransaction
from schemas import TransactionCreate, RecurringTransactionCreate
from security import get_current_user

from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange

router = APIRouter(prefix="/transactions", tags=["Expenses"])


def calculate_next_due(current_date: datetime, frequency: str) -> datetime:
    """Given a date and a frequency, return the next due date."""
    if frequency == "daily":
        return current_date + timedelta(days=1)
    elif frequency == "weekly":
        return current_date + timedelta(weeks=1)
    elif frequency == "monthly":
        return current_date + relativedelta(months=1)
    elif frequency == "yearly":
        return current_date + relativedelta(years=1)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")


#add transaction
@router.post("/add")
def create_transaction(
    transaction: TransactionCreate,
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
    db: Session = Depends(get_db)
):
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

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

    return {
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
    results = db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("total_amount")).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense"
        ).group_by(Transaction.category)
    ).all()

    return {
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


#add recurring transaction — creates the recurring rule AND fires the first transaction immediately
@router.post("/add/recurring")
def create_recurring_transaction(
    recurring_transaction: RecurringTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    next_due = calculate_next_due(recurring_transaction.start_date, recurring_transaction.frequency)

    new_recurring_transaction = RecurringTransaction(
        amount=recurring_transaction.amount,
        type=recurring_transaction.type,
        category=recurring_transaction.category,
        description=recurring_transaction.description,
        frequency=recurring_transaction.frequency,
        start_date=recurring_transaction.start_date,
        next_due=next_due,
        user_id=current_user.id
    )
    db.add(new_recurring_transaction)
    db.flush()  # assigns new_recurring_transaction.id without committing yet

    # Fire the first transaction immediately, dated to the start_date
    initial_transaction = Transaction(
        amount=recurring_transaction.amount,
        type=recurring_transaction.type,
        category=recurring_transaction.category,
        description=recurring_transaction.description,
        created_at=recurring_transaction.start_date,
        user_id=current_user.id
    )
    db.add(initial_transaction)

    db.commit()
    db.refresh(new_recurring_transaction)
    db.refresh(initial_transaction)

    return {
        "message": "Recurring transaction added successfully",
        "recurring_transaction_id": new_recurring_transaction.id,
        "initial_transaction_id": initial_transaction.id,
        "next_due": new_recurring_transaction.next_due
    }


#pause a recurring transaction — freezes it. next_due is left untouched and
#simply ignored by the scheduler while inactive 
@router.patch("/recurring/{recurring_id}/pause")
def pause_recurring_transaction(
    recurring_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recurring = db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    if not recurring.active:
        return {"message": "Recurring transaction is already paused"}

    recurring.active = False
    db.commit()
    return {"message": "Recurring transaction paused successfully"}


#resume a recurring transaction — restarts the cycle from right now
#no back-fill, no skipping through missed dates,
#next_due becomes "now + one interval")
@router.patch("/recurring/{recurring_id}/resume")
def resume_recurring_transaction(
    recurring_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recurring = db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    if recurring.active:
        return {"message": "Recurring transaction is already active"}

    now = datetime.now(timezone.utc)
    recurring.next_due = calculate_next_due(now, recurring.frequency)
    recurring.active = True
    db.commit()

    return {
        "message": "Recurring transaction resumed successfully",
        "next_due": recurring.next_due
    }


#delete a recurring transaction — past transactions it already generated stay untouched
@router.delete("/recurring/{recurring_id}")
def delete_recurring_transaction(
    recurring_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recurring = db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    db.delete(recurring)
    db.commit()
    return {"message": "Recurring transaction deleted successfully. Past transactions remain unaffected."}

#get all recurring transactions for the user
@router.get("/recurring/all")
def get_all_recurring_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recurring_transactions = db.execute(
        select(RecurringTransaction).where(RecurringTransaction.user_id == current_user.id)
    ).scalars().all()

    return [
        {
            "id": r.id,
            "category": r.category,
            "amount": r.amount,
            "type": r.type,
            "frequency": r.frequency,
            "next_due": r.next_due,
            "active": r.active
        }
        for r in recurring_transactions
    ]