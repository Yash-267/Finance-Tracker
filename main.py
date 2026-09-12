from fastapi import FastAPI
from database import Base, engine
from models import User, Transaction
import asyncio
from contextlib import asynccontextmanager

from router import auth, expense           # scheduler not needed here anymore
from router.scheduler import recurring_transaction_scheduler, process_due_recurring_transactions

@asynccontextmanager
async def lifespan(app: FastAPI):
    # catch up immediately on startup — covers time the server was off
    process_due_recurring_transactions()
    task = asyncio.create_task(recurring_transaction_scheduler())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan, title="Finance Tracker")

app.include_router(auth.router)
app.include_router(expense.router)

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Welcome to the personal finance app!"}