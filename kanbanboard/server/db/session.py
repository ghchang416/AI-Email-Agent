import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

DB_USER = os.getenv("KANBAN_DB_USER", "kanban_user")
DB_PASSWORD = os.getenv("KANBAN_DB_PASSWORD", "kanban_pw")
DB_HOST = os.getenv("KANBAN_DB_HOST", "kanban_db")
DB_NAME = os.getenv("KANBAN_DB_NAME", "kanban_db")

# PostgreSQL 연결 문자열 생성
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db() -> Session: # type: ignore
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
Base = declarative_base()