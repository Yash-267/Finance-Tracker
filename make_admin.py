from database import SessionLocal
from models import User

db = SessionLocal()

user = db.query(User).filter(User.email == "ash@test").first()

if user:
    user.role = "admin"
    db.commit()
    print("User promoted to admin")
else:
    print("User not found")

db.close()