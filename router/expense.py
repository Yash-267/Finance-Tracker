from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database import get_db
from models import Transaction, User, RecurringTransaction, Budget, BudgetAlert
from schemas import TransactionCreate, RecurringTransactionCreate
from security import get_current_user

from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange

router = APIRouter(prefix="/transactions", tags=["Expenses"])

def ensure_utc(dt: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC, treating naive datetimes as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

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


def check_budget_thresholds(db: Session, user_id: int, category: str, transaction_date: datetime) -> None:
    """Called right after an expense transaction is inserted (manual or
    recurring-generated — both flow through the same Transaction table).
    Checks whether this category's spend, for the MONTH THE TRANSACTION
    BELONGS TO, has crossed 80% or 100% of the user's budget for that
    category, and logs an alert exactly once per threshold per month.
    Does not commit — the caller commits alongside its own changes."""
    budget = db.execute(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category == category,
            Budget.active == True
        )
    ).scalar_one_or_none()

    if not budget:
        return

    year = transaction_date.year
    month = transaction_date.month

    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    spent = db.scalar(
        select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user_id,
            Transaction.category == category,
            Transaction.type == "expense",
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        )
    ) or 0

    if spent >= budget.monthly_limit:
        threshold = "exceeded"
        message = f"You've exceeded your {category} budget of ₹{budget.monthly_limit:.2f} — spent ₹{spent:.2f} this month."
    elif spent >= 0.8 * budget.monthly_limit:
        threshold = "approaching"
        percent = spent / budget.monthly_limit * 100
        message = f"You've used {percent:.0f}% of your {category} budget this month (₹{spent:.2f} of ₹{budget.monthly_limit:.2f})."
    else:
        return

    already_alerted = db.execute(
        select(BudgetAlert).where(
            BudgetAlert.budget_id == budget.id,
            BudgetAlert.year == year,
            BudgetAlert.month == month,
            BudgetAlert.threshold == threshold
        )
    ).scalar_one_or_none()

    if already_alerted:
        return

    db.add(BudgetAlert(
        budget_id=budget.id,
        user_id=user_id,
        threshold=threshold,
        year=year,
        month=month,
        message=message
    ))


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

    if new_transaction.type == "expense":
        check_budget_thresholds(db, current_user.id, new_transaction.category, new_transaction.created_at)
        db.commit()

    return {"message": "Transaction added successfully", "transaction_id": new_transaction.id}


#get all transactions
@router.get("/all")
def get_all_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())).scalars().all()
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
    start_date = ensure_utc(recurring_transaction.start_date)
    now = datetime.now(timezone.utc)
    starts_in_future = start_date > now

    next_due = start_date if starts_in_future else calculate_next_due(start_date, recurring_transaction.frequency)

    new_recurring_transaction = RecurringTransaction(
        amount=recurring_transaction.amount,
        type=recurring_transaction.type,
        category=recurring_transaction.category,
        description=recurring_transaction.description,
        frequency=recurring_transaction.frequency,
        start_date=start_date,
        next_due=next_due,
        user_id=current_user.id
    )
    db.add(new_recurring_transaction)
    db.flush()

    initial_transaction = None
    if not starts_in_future:
        initial_transaction = Transaction(
            amount=recurring_transaction.amount,
            type=recurring_transaction.type,
            category=recurring_transaction.category,
            description=recurring_transaction.description,
            created_at=start_date,
            user_id=current_user.id
        )
        db.add(initial_transaction)

    db.commit()
    db.refresh(new_recurring_transaction)
    if initial_transaction:
        db.refresh(initial_transaction)
        if initial_transaction.type == "expense":
            check_budget_thresholds(db, current_user.id, initial_transaction.category, initial_transaction.created_at)
            db.commit()

    return {
        "message": (
            "Recurring transaction scheduled — it will start once the start date arrives"
            if starts_in_future
            else "Recurring transaction added successfully"
        ),
        "recurring_transaction_id": new_recurring_transaction.id,
        "initial_transaction_id": initial_transaction.id if initial_transaction else None,
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
            "description": r.description,
            "next_due": r.next_due,
            "active": r.active
        }
        for r in recurring_transactions
    ]