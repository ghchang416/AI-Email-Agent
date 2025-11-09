import logging
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from repositories.user import UserRepository
from repositories.task import TaskRepository
from schemas.user import UserUpdate, UserSchema, KanbanUserStatusSchema, UserCreate
from db.session import get_db
from typing import List

logger = logging.getLogger(__name__)

TASK_OVERLOAD_THRESHOLD = 10 # 10개 이상이면 'Overloaded'로 간주

class UserService:
    """ User 관련 비즈니스 로직을 담당합니다. (예: 상태 판별) """
    
    def __init__(self, db: Session = Depends(get_db)):
        self.user_repo = UserRepository(db)
        self.task_repo = TaskRepository(db)

    def create_new_user(self, user_create: UserCreate) -> UserSchema:
        """ 새로운 사용자를 생성합니다. (이메일 중복 검사 포함) """
        existing_user = self.user_repo.get_user_by_email(user_create.email)
        if existing_user:
            logger.warning(f"Failed to create user. Email already exists: {user_create.email}")
            
            raise HTTPException(
                status_code=409, 
                detail="User with this email already exists"
            )
            
        logger.info(f"Creating new user: {user_create.email}")
        return self.user_repo.create_user(user_create)

    def get_user_by_id(self, user_id: int) -> UserSchema:
        """ ID로 사용자 조회 """
        db_user = self.user_repo.get_user_by_id(user_id)
        if not db_user:
            logger.warning(f"User not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return db_user

    def get_all_users(self) -> List[UserSchema]:
        """ 모든 사용자 조회 """
        return self.user_repo.get_users()

    def update_user_status(self, user_id: int, user_update: UserUpdate) -> UserSchema:
        """ 사용자 정보 수정 """
        db_user = self.user_repo.update_user(user_id, user_update)
        if not db_user:
            logger.warning(f"Failed to update user. User not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return db_user
    
    def get_user_status_for_kanban(self, email: str) -> KanbanUserStatusSchema:
        """
        GetKanbanUserStatusTool이 호출할 비즈니스 로직.
        DB 상태와 업무량을 조합하여 최종 상태를 판별합니다.
        """
        user = self.user_repo.get_user_by_email(email)
        if not user:
            logger.warning(f"Kanban status check failed. User not found for email: {email}")
            raise HTTPException(status_code=404, detail=f"User with email {email} not found")
        
        raw_db_status = user.status
        
        if raw_db_status == "휴가 중":
            return KanbanUserStatusSchema(
                email=user.email,
                status="Vacation", 
                message="User is currently on vacation.",
                active_task_count=0, # 휴가 중이므로 작업량 무관
                raw_db_status=raw_db_status
            )
        
        task_count = self.task_repo.get_active_task_count_by_user(user.id)
        
        if task_count >= TASK_OVERLOAD_THRESHOLD:
            return KanbanUserStatusSchema(
                email=user.email,
                status="Overloaded",
                message=f"User has {task_count} active tasks (Threshold: {TASK_OVERLOAD_THRESHOLD}).",
                active_task_count=task_count,
                raw_db_status=raw_db_status
            )
            
        return KanbanUserStatusSchema(
            email=user.email,
            status="Available",
            message=f"User status is '{raw_db_status}' with {task_count} active tasks.",
            active_task_count=task_count,
            raw_db_status=raw_db_status
        )