"""
Database connection and session setup.

Local dev: SQLite (backend/data/twinops.db), used automatically when
no DATABASE_URL environment variable is set.

Production: set DATABASE_URL to a Postgres connection string (e.g.
from Supabase) and this switches over with no code changes needed
anywhere else — every model/route uses the same SessionLocal/Base
regardless of which database is behind it.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/twinops.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
