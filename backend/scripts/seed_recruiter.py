"""
Run once to create a test recruiter account.
Usage: PYTHONPATH=. python scripts/seed_recruiter.py
"""
import uuid
import datetime
from app.db.database import SessionLocal
from app.db.models import Recruiter
from app.core.security import hash_password

def seed():
    db = SessionLocal()
    try:
        existing = db.query(Recruiter).filter(
            Recruiter.email == "admin@demo.com"
        ).first()
        if existing:
            print("Recruiter already exists — skipping")
            return

        recruiter = Recruiter(
            id=uuid.uuid4(),
            email="admin@demo.com",
            hashed_password=hash_password("password"),
            full_name="Demo Recruiter",
            created_at=datetime.datetime.utcnow()
        )
        db.add(recruiter)
        db.commit()
        print("✅ Recruiter created: admin@demo.com / password")
    finally:
        db.close()

if __name__ == "__main__":
    seed()