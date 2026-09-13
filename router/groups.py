from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models import User, Group, GroupMember, GroupExpense, ExpenseShare, Settlement
from schemas import GroupCreate, GroupMemberAdd, GroupExpenseCreate, SettlementCreate
from security import get_current_user

router = APIRouter(prefix="/groups", tags=["Bill Splitting"])


def ensure_group_member(db: Session, group_id: int, user_id: int) -> None:
    is_member = db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    ).scalar_one_or_none()
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this group")


def get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def calculate_group_balances(db: Session, group_id: int) -> dict:
    """Logic - Derives net pairwise balances within a group from every expense share
    and settlement on record — nothing is ever stored as 'current balance'.
    Returns {(ower_id, payer_id): amount}, netted down to one direction per pair."""
    raw = defaultdict(float)

    rows = db.execute(
        select(ExpenseShare, GroupExpense.paid_by)
        .join(GroupExpense, ExpenseShare.group_expense_id == GroupExpense.id)
        .where(GroupExpense.group_id == group_id)
    ).all()

    for share, paid_by in rows:
        if share.user_id != paid_by:
            raw[(share.user_id, paid_by)] += share.share_amount

    settlements = db.execute(
        select(Settlement).where(Settlement.group_id == group_id)
    ).scalars().all()

    for s in settlements:
        raw[(s.paid_by, s.paid_to)] -= s.amount

    net = {}
    seen = set()
    for (a, b) in list(raw.keys()):
        if (a, b) in seen or (b, a) in seen:
            continue
        seen.add((a, b))
        difference = round(raw.get((a, b), 0) - raw.get((b, a), 0), 2)
        if difference > 0:
            net[(a, b)] = difference
        elif difference < 0:
            net[(b, a)] = -difference

    return net


#create a group — creator is automatically the first member
@router.post("/create")
def create_group(
    group: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_group = Group(name=group.name, created_by=current_user.id)
    db.add(new_group)
    db.flush()

    db.add(GroupMember(group_id=new_group.id, user_id=current_user.id))
    db.commit()
    db.refresh(new_group)

    return {"message": "Group created successfully", "group_id": new_group.id}


#add a member to a group by email — only existing members can add others
@router.post("/{group_id}/members")
def add_member(
    group_id: int,
    member: GroupMemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_group_or_404(db, group_id)
    ensure_group_member(db, group_id, current_user.id)

    target_user = db.execute(select(User).where(User.email == member.email)).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="No user found with that email")

    already_member = db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == target_user.id)
    ).scalar_one_or_none()
    if already_member:
        raise HTTPException(status_code=400, detail="User is already a member of this group")

    db.add(GroupMember(group_id=group_id, user_id=target_user.id))
    db.commit()

    return {"message": f"{target_user.username} added to the group"}


#list every group the current user belongs to
@router.get("/")
def list_my_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    groups = db.execute(
        select(Group).join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == current_user.id)
    ).scalars().all()

    return [{"id": g.id, "name": g.name, "created_by": g.created_by, "created_at": g.created_at} for g in groups]


#group details, including its member list
@router.get("/{group_id}")
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_group_or_404(db, group_id)
    ensure_group_member(db, group_id, current_user.id)

    members = db.execute(
        select(User).join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
    ).scalars().all()

    return {
        "id": group_id,
        "members": [{"id": m.id, "username": m.username, "email": m.email} for m in members]
    }


#add a shared expense to a group, with an equal or custom split
@router.post("/{group_id}/expenses")
def create_group_expense(
    group_id: int,
    expense: GroupExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_group_or_404(db, group_id)
    ensure_group_member(db, group_id, current_user.id)

    member_ids = {
        m.user_id for m in db.execute(
            select(GroupMember).where(GroupMember.group_id == group_id)
        ).scalars().all()
    }

    if expense.split_type == "equal":
        participants = expense.participant_ids or list(member_ids)
        invalid = set(participants) - member_ids
        if invalid:
            raise HTTPException(status_code=400, detail=f"User(s) {invalid} are not members of this group")
        if not participants:
            raise HTTPException(status_code=400, detail="At least one participant is required")

        n = len(participants)
        base_share = round(expense.amount / n, 2)
        shares = {uid: base_share for uid in participants}

        # equal division rarely divides exactly — push the rounding remainder
        # onto the last participant so shares always sum to the exact total
        drift = round(expense.amount - base_share * n, 2)
        shares[participants[-1]] = round(shares[participants[-1]] + drift, 2)

    else:  # custom
        if not expense.custom_shares:
            raise HTTPException(status_code=400, detail="custom_shares is required for a custom split")

        invalid = {s.user_id for s in expense.custom_shares} - member_ids
        if invalid:
            raise HTTPException(status_code=400, detail=f"User(s) {invalid} are not members of this group")

        total_shares = round(sum(s.amount for s in expense.custom_shares), 2)
        if abs(total_shares - round(expense.amount, 2)) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Custom shares (₹{total_shares}) must add up to the total amount (₹{expense.amount})"
            )
        shares = {s.user_id: s.amount for s in expense.custom_shares}

    new_expense = GroupExpense(
        group_id=group_id,
        paid_by=current_user.id,
        amount=expense.amount,
        description=expense.description
    )
    db.add(new_expense)
    db.flush()

    for user_id, share_amount in shares.items():
        db.add(ExpenseShare(group_expense_id=new_expense.id, user_id=user_id, share_amount=share_amount))

    db.commit()
    db.refresh(new_expense)

    return {"message": "Group expense added successfully", "expense_id": new_expense.id, "shares": shares}


#list every expense logged in a group, with each person's share
@router.get("/{group_id}/expenses")
def list_group_expenses(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_group_or_404(db, group_id)
    ensure_group_member(db, group_id, current_user.id)

    expenses = db.execute(
        select(GroupExpense).where(GroupExpense.group_id == group_id)
        .order_by(GroupExpense.created_at.desc())
    ).scalars().all()

    result = []
    for e in expenses:
        shares = db.execute(select(ExpenseShare).where(ExpenseShare.group_expense_id == e.id)).scalars().all()
        result.append({
            "id": e.id,
            "description": e.description,
            "amount": e.amount,
            "paid_by": e.paid_by,
            "created_at": e.created_at,
            "shares": [{"user_id": s.user_id, "amount": s.share_amount} for s in shares]
        })
    return result


#record a settlement — the current user repaying someone else in the group
@router.post("/{group_id}/settle")
def create_settlement(
    group_id: int,
    settlement: SettlementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_group_or_404(db, group_id)
    ensure_group_member(db, group_id, current_user.id)
    ensure_group_member(db, group_id, settlement.paid_to)

    if settlement.paid_to == current_user.id:
        raise HTTPException(status_code=400, detail="You can't settle up with yourself")

    new_settlement = Settlement(
        group_id=group_id,
        paid_by=current_user.id,
        paid_to=settlement.paid_to,
        amount=settlement.amount
    )
    db.add(new_settlement)
    db.commit()
    db.refresh(new_settlement)

    return {"message": "Settlement recorded successfully", "settlement_id": new_settlement.id}


#who owes who, within a group — computed live from expenses and settlements
@router.get("/{group_id}/balances")
def get_group_balances(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_group_or_404(db, group_id)
    ensure_group_member(db, group_id, current_user.id)

    net = calculate_group_balances(db, group_id)

    involved_ids = {uid for pair in net for uid in pair}
    users = {}
    if involved_ids:
        users = {u.id: u for u in db.execute(select(User).where(User.id.in_(involved_ids))).scalars().all()}

    balances = [
        {
            "owed_by_id": ower_id,
            "owed_by_username": users[ower_id].username,
            "owed_to_id": payer_id,
            "owed_to_username": users[payer_id].username,
            "amount": amount
        }
        for (ower_id, payer_id), amount in net.items()
    ]

    return {"balances": balances}