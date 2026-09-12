import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from database import SessionLocal  # requires SessionLocal to be exported from database.py
from models import RecurringTransaction, Transaction
from router.expense import calculate_next_due

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60  # how often to poll for due recurring transactions


def process_due_recurring_transactions() -> None:
    """Find every active recurring transaction that is due (or overdue),
    generate the missed transaction(s), and advance next_due until it's
    in the future. Only touches active rows — paused ones are skipped
    entirely, exactly as intended. Safe to call repeatedly / on startup."""
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
                db.add(Transaction(
                    amount=recurring.amount,
                    type=recurring.type,
                    category=recurring.category,
                    description=recurring.description,
                    created_at=recurring.next_due,
                    user_id=recurring.user_id
                ))
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