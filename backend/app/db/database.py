from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# 1. Force clean the URL: removes accidental spaces, quotes, or line breaks
clean_url = settings.DATABASE_URL.replace('"', '').replace("'", "").strip()

# 2. Add a quick safety check
if not clean_url.startswith("postgresql://"):
    raise ValueError(f"CRITICAL: Invalid URL format detected! URL looks like: {clean_url}")

# 3. Build the engine with the cleaned URL
engine = create_engine(clean_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()