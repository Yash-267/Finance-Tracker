from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from pydantic import BaseModel
from typing import Literal
from datetime import datetime, timezone

from database import get_db

from models import User, Transaction, RecurringTransaction
from security import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

class RoleUpdate(BaseModel):
    role: Literal["user", "admin"]


@router.get("/dashboard")
def admin_dashboard(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_transactions = db.scalar(select(func.count(Transaction.id))) or 0
    total_volume = db.scalar(select(func.sum(Transaction.amount))) or 0

    top_categories = db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("total_amount"))
        .where(Transaction.type == "expense")
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
    ).all()

    active_recurring = db.scalar(
        select(func.count(RecurringTransaction.id)).where(RecurringTransaction.active == True)
    ) or 0
    paused_recurring = db.scalar(
        select(func.count(RecurringTransaction.id)).where(RecurringTransaction.active == False)
    ) or 0

    now = datetime.now(timezone.utc)
    overdue_recurring = db.scalar(
        select(func.count(RecurringTransaction.id)).where(
            RecurringTransaction.active == True,
            RecurringTransaction.next_due < now
        )
    ) or 0

    return {
        "total_users": total_users,
        "total_transactions": total_transactions,
        "total_transaction_volume": float(total_volume),
        "top_categories_platform_wide": [
            {"category": category, "total_amount": float(total_amount)}
            for category, total_amount in top_categories
        ],
        "active_recurring": active_recurring,
        "paused_recurring": paused_recurring,
        "overdue_recurring": overdue_recurring
    }


#List all users, for the role-management table
@router.get("/users")
def list_users(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.execute(select(User)).scalars().all()
    return [
        {"id": u.id, "username": u.username, "email": u.email, "role": u.role, "created_at": u.created_at}
        for u in users
    ]


#Promote or demote a user
@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role_update: RoleUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_admin.id and role_update.role == "user":
        raise HTTPException(status_code=400, detail="You can't demote yourself")

    target_user.role = role_update.role
    db.commit()
    return {"message": f"User {target_user.email} role updated to {role_update.role}"}


#Every recurring transaction across all users, flagging overdue ones
#(overdue = active and next_due already passed — usually means the scheduler missed a cycle)
@router.get("/recurring")
def list_all_recurring(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    recurring = db.execute(select(RecurringTransaction)).scalars().all()
    return [
        {
            "id": r.id, "user_id": r.user_id, "category": r.category, "amount": r.amount,
            "frequency": r.frequency, "next_due": r.next_due, "active": r.active,
            "overdue": r.active and r.next_due < now
        }
        for r in recurring
    ]