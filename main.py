from fastapi import FastAPI
from database import Base, engine
from models import User, Transaction
from router import auth,expense

app = FastAPI(title = "personal finance app")
app.include_router(auth.router)
app.include_router(expense.router)

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Welcome to the personal finance app!"}