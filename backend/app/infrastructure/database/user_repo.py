import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List

from app.infrastructure.database.models import User
from app.core.security import hash_password
from app.core.exceptions import DatabaseError, DuplicateError

logger = logging.getLogger("smart_inventory.repo.user")


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except SQLAlchemyError as e:
            logger.error("Database error getting user by id: %s", str(e))
            raise DatabaseError(f"Failed to get user: {str(e)}")

    def get_by_email(self, email: str) -> Optional[User]:
        try:
            return self.db.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            logger.error("Database error getting user by email: %s", str(e))
            raise DatabaseError(f"Failed to get user: {str(e)}")

    def get_by_username(self, username: str) -> Optional[User]:
        try:
            return self.db.query(User).filter(User.username == username).first()
        except SQLAlchemyError as e:
            logger.error("Database error getting user by username: %s", str(e))
            raise DatabaseError(f"Failed to get user: {str(e)}")

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        try:
            return self.db.query(User).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error("Database error listing users: %s", str(e))
            raise DatabaseError(f"Failed to list users: {str(e)}")

    def create(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "staff",
    ) -> User:
        try:
            hashed = hash_password(password)
            user = User(
                email=email,
                username=username,
                hashed_password=hashed,
                full_name=full_name,
                role=role,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            self.db.rollback()
            if "UNIQUE constraint" in str(e) or "duplicate" in str(e).lower():
                raise DuplicateError("User with this email or username already exists")
            logger.error("Database error creating user: %s", str(e))
            raise DatabaseError(f"Failed to create user: {str(e)}")

    def update(self, user: User) -> User:
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error updating user: %s", str(e))
            raise DatabaseError(f"Failed to update user: {str(e)}")

    def delete(self, user_id: int) -> bool:
        try:
            user = self.get_by_id(user_id)
            if user:
                self.db.delete(user)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Database error deleting user: %s", str(e))
            raise DatabaseError(f"Failed to delete user: {str(e)}")

    def count(self) -> int:
        try:
            return self.db.query(User).count()
        except SQLAlchemyError as e:
            logger.error("Database error counting users: %s", str(e))
            raise DatabaseError(f"Failed to count users: {str(e)}")
