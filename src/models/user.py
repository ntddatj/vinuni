from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"

    @staticmethod
    def is_first_user(session) -> bool:
        """Return True if there are no users in the database yet."""
        return session.query(User).first() is None
