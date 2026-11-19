from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from schemas import AccountDelete, ForgotPassword, ResetPassword, UserCreate, UserLogin
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import delete, func, or_, select, update
from models import (
    Budget, BudgetAlert, ExpenseShare, Group, GroupExpense, GroupMember,
    PasswordResetToken, RecurringTransaction, Settlement, Transaction, User,
)
from database import SessionLocal, get_db
from mailer import send_password_reset
from security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def issue_password_reset(email: str) -> None:
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        if user_id is None:
            return

        token = token_urlsafe(32)
        token_hash = sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        # At most one reset email per account every five minutes.
        replaced = db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.expires_at <= expires_at - timedelta(minutes=5),
            )
            .values(token_hash=token_hash, expires_at=expires_at)
            .returning(PasswordResetToken.user_id)
        ).scalar_one_or_none()
        if replaced is None:
            if db.get(PasswordResetToken, user_id) is not None:
                return
            db.add(PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at))
        try:
            db.commit()
        except IntegrityError:
            # A concurrent request already inserted a token, or the user was deleted.
            db.rollback()
            return

    send_password_reset(email, token)


@router.post("/forgot-password", status_code=202)
def forgot_password(request: ForgotPassword, background_tasks: BackgroundTasks):
    background_tasks.add_task(issue_password_reset, request.email.strip())
    return {"message": "If an account matches that email, a reset link will be sent."}


@router.post("/reset-password", status_code=204)
def reset_password(request: ResetPassword, db: Session = Depends(get_db)):
    user_id = db.execute(
        delete(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == sha256(request.token.encode()).hexdigest(),
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
        .returning(PasswordResetToken.user_id)
    ).scalar_one_or_none()
    if user_id is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    db.execute(update(User).where(User.id == user_id).values(hashed_password=hash_password(request.password)))
    db.commit()

#Register a new user
@router.post("/register")
def register_user(user: UserCreate, db:Session = Depends(get_db)):

    #if the user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    #create new user
    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "user_id": new_user.id}

#Login
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.execute(select(User).where(User.email == user.email)).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = create_access_token(db_user)
    return {
        "message": "Login successful",
        "access_token": token, 
        "token_type": "bearer", 
        "user_id": db_user.id
    }   

#Current user profile
@router.get("/me")
def profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role
    }


@router.delete("/me", status_code=204)
def delete_account(
    confirmation: AccountDelete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(confirmation.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")

    user_id = current_user.id
    # Preserve shared groups by assigning ownership to the earliest remaining member.
    successor = (
        select(GroupMember.user_id)
        .where(GroupMember.group_id == Group.id, GroupMember.user_id != user_id)
        .order_by(GroupMember.joined_at, GroupMember.id)
        .limit(1)
        .scalar_subquery()
    )
    db.execute(
        update(Group).where(Group.created_by == user_id, successor.is_not(None))
        .values(created_by=successor)
    )
    owned_groups = select(Group.id).where(Group.created_by == user_id)
    removed_expenses = or_(GroupExpense.paid_by == user_id, GroupExpense.group_id.in_(owned_groups))
    expense_ids = select(GroupExpense.id).where(removed_expenses)
    budget_ids = select(Budget.id).where(Budget.user_id == user_id)

    db.execute(delete(ExpenseShare).where(or_(
        ExpenseShare.user_id == user_id, ExpenseShare.group_expense_id.in_(expense_ids),
    )))
    db.execute(delete(GroupExpense).where(removed_expenses))
    db.execute(delete(Settlement).where(or_(
        Settlement.paid_by == user_id, Settlement.paid_to == user_id,
        Settlement.group_id.in_(owned_groups),
    )))
    db.execute(delete(GroupMember).where(or_(
        GroupMember.user_id == user_id, GroupMember.group_id.in_(owned_groups),
    )))
    db.execute(delete(Group).where(Group.created_by == user_id))
    db.execute(delete(BudgetAlert).where(or_(
        BudgetAlert.user_id == user_id, BudgetAlert.budget_id.in_(budget_ids),
    )))
    for model in (Budget, Transaction, RecurringTransaction):
        db.execute(delete(model).where(model.user_id == user_id))
    db.delete(current_user)
    db.commit()
