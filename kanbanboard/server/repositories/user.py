from sqlalchemy.orm import Session
from db.models import User
from schemas.user import UserCreate, UserUpdate
from typing import List, Optional

class UserRepository:
    """ User 모델에 대한 데이터베이스 CRUD 연산을 담당합니다. """
    
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ ID로 사용자 1명 조회 """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """ 이메일로 사용자 1명 조회 """
        return self.db.query(User).filter(User.email == email).first()

    def get_users(self) -> List[User]:
        """ 모든 사용자 조회 """
        return self.db.query(User).all()

    def create_user(self, user: UserCreate) -> User:
        """ 사용자 생성 """
        db_user = User(**user.dict())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """ 사용자 정보 수정 """
        db_user = self.get_user_by_id(user_id)
        if db_user:
            update_data = user_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user
    
    def count_users(self) -> int:
        return self.db.query(User).count()