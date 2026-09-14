from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from database import get_db
from models import User, Transaction, Budget, BudgetAlert
from schemas import BudgetCreate, BudgetUpdate
from security import get_current_user

from datetime import datetime, timezone
from calendar import monthrange

router = APIRouter(prefix="/budgets", tags=["Budgets"])


#create a budget — one active budget per category per user
@router.post("/create")
def create_budget(
    budget: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.execute(
        select(Budget).where(
            Budget.user_id == current_user.id,
            Budget.category == budget.category,
            Budget.active == True
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"An active budget already exists for {budget.category} — update it instead"
        )

    new_budget = Budget(
        user_id=current_user.id,
        category=budget.category,
        monthly_limit=budget.monthly_limit
    )
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)

    return {"message": "Budget created successfully", "budget_id": new_budget.id}


#list all budgets with this calendar month's spend and % used
@router.get("/all")
def list_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    budgets = db.execute(
        select(Budget).where(Budget.user_id == current_user.id)
    ).scalars().all()

    now = datetime.now(timezone.utc)
    start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    last_day = monthrange(now.year, now.month)[1]
    end_date = datetime(now.year, now.month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    result = []
    for b in budgets:
        spent = db.scalar(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == current_user.id,
                Transaction.category == b.category,
                Transaction.type == "expense",
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date
            )
        ) or 0

        result.append({
            "id": b.id,
            "category": b.category,
            "monthly_limit": b.monthly_limit,
            "active": b.active,
            "spent_this_month": float(spent),
            "percent_used": round((spent / b.monthly_limit) * 100, 1) if b.monthly_limit else 0
        })

    return result


#update a budget's limit
@router.patch("/{budget_id}")
def update_budget(
    budget_id: int,
    budget_update: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    budget = db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == current_user.id)
    ).scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    budget.monthly_limit = budget_update.monthly_limit
    db.commit()

    return {"message": "Budget updated successfully"}


#delete a budget — also clears its alert history so nothing dangles
@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    budget = db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == current_user.id)
    ).scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.execute(delete(BudgetAlert).where(BudgetAlert.budget_id == budget_id))
    db.delete(budget)
    db.commit()

    return {"message": "Budget deleted successfully"}


@router.get("/alerts")
def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alerts = db.execute(
        select(BudgetAlert).where(BudgetAlert.user_id == current_user.id)
        .order_by(BudgetAlert.created_at.desc())
    ).scalars().all()

    return [
        {
            "id": a.id,
            "budget_id": a.budget_id,
            "threshold": a.threshold,
            "message": a.message,
            "read": a.read,
            "created_at": a.created_at
        }
        for a in alerts
    ]

@router.patch("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = db.execute(
        select(BudgetAlert).where(BudgetAlert.id == alert_id, BudgetAlert.user_id == current_user.id)
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.read = True
    db.commit()

    return {"message": "Alert marked as read"}