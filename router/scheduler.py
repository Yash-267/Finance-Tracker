import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from database import SessionLocal 
from models import RecurringTransaction, Transaction
from router.expense import calculate_next_due, check_budget_thresholds

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60  


def process_due_recurring_transactions() -> None:

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_recurring = db.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.active == True,
                RecurringTransaction.next_due <= now
            )
        ).scalars().all()

        for recurring in due_recurring:
            while recurring.next_due <= now:
                new_txn = Transaction(
                    amount=recurring.amount,
                    type=recurring.type,
                    category=recurring.category,
                    description=recurring.description,
                    created_at=recurring.next_due,
                    user_id=recurring.user_id
                )
                db.add(new_txn)
                # Flush so this row is visible to the SUM() query inside
                # check_budget_thresholds — without this, a category that
                # catches up on several missed cycles in one run would
                # under-count spend on every iteration but the last.
                db.flush()

                if new_txn.type == "expense":
                    check_budget_thresholds(db, recurring.user_id, recurring.category, new_txn.created_at)

                recurring.next_due = calculate_next_due(recurring.next_due, recurring.frequency)

        db.commit()
    except Exception:
        logger.exception("Error while processing recurring transactions")
        db.rollback()
    finally:
        db.close()


async def recurring_transaction_scheduler() -> None:
    """Background loop — run this as an asyncio task from app startup."""
    while True:
        await asyncio.to_thread(process_due_recurring_transactions)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)