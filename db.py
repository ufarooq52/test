from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, create_engine, UniqueConstraint, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.hash import bcrypt

DATABASE_URL = "sqlite:////workspace/swatch.db"

Base = declarative_base()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    free_downloads_remaining = Column(Integer, default=10, nullable=False)
    paid_credits = Column(Integer, default=0, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    stripe_session_id = Column(String, nullable=False)
    credits_added = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("stripe_session_id", name="uq_purchase_session"),
    )


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db_session() -> Session:
    return SessionLocal()


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.verify(password, password_hash)
    except Exception:
        return False


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).one_or_none()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).one_or_none()


def create_user(db: Session, email: str, password: str) -> User:
    existing = get_user_by_email(db, email)
    if existing is not None:
        raise ValueError("Email already registered")
    user = User(
        email=email.strip().lower(),
        password_hash=hash_password(password),
        free_downloads_remaining=10,
        paid_credits=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email.strip().lower())
    if user and verify_password(password, user.password_hash):
        return user
    return None


def decrement_download_credit(db: Session, user: User) -> None:
    if user.free_downloads_remaining > 0:
        user.free_downloads_remaining -= 1
    elif user.paid_credits > 0:
        user.paid_credits -= 1
    else:
        raise ValueError("No credits available")
    db.add(user)
    db.commit()


def add_paid_credits(db: Session, user: User, amount: int) -> None:
    user.paid_credits += amount
    db.add(user)
    db.commit()


def record_purchase(db: Session, user: User, stripe_session_id: str, credits_added: int) -> Purchase:
    purchase = Purchase(
        user_id=user.id,
        stripe_session_id=stripe_session_id,
        credits_added=credits_added,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase


def has_processed_session(db: Session, stripe_session_id: str) -> bool:
    existing = db.query(Purchase).filter(Purchase.stripe_session_id == stripe_session_id).one_or_none()
    return existing is not None