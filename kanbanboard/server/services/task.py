import logging
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from repositories.task import TaskRepository
from repositories.user import UserRepository
from schemas.task import KanbanTaskCreateSchema, TaskUpdate, TaskSchema
from db.session import get_db
from typing import List, Optional

logger = logging.getLogger(__name__)

class TaskService:
    """ Task 관련 비즈니스 로직을 담당합니다. (예: 이메일로 담당자 ID 찾기) """
    
    def __init__(self, db: Session = Depends(get_db)):
        self.user_repo = UserRepository(db)
        self.task_repo = TaskRepository(db)

    def get_tasks_for_assignee(self, assignee_id: Optional[int] = None) -> List[TaskSchema]:
        """ 모든 Task 또는 특정 담당자의 Task 조회 """
        if assignee_id:
            return self.task_repo.get_tasks_by_assignee(assignee_id)
        return self.task_repo.get_all_tasks()

    def create_task_from_webhook_payload(self, task_data: KanbanTaskCreateSchema) -> TaskSchema:
        """
        SendTaskToKanbanTool의 페이로드를 받아 Task를 생성합니다.
        1. 이메일로 담당자(User)를 찾습니다.
        2. 담당자 ID를 포함하여 Task를 생성합니다.
        """
        assignee_email = task_data.final_assignee_email
        assignee = self.user_repo.get_user_by_email(assignee_email)
        
        if not assignee:
            logger.error(f"Cannot create task. Assignee user not found for email: {assignee_email}")
            raise HTTPException(
                status_code=404, 
                detail=f"Assignee user with email {assignee_email} not found. Cannot create task."
            )
        
        if assignee.name != task_data.final_assignee_name:
            logger.warning(
                f"Assignee name mismatch for {assignee_email}. "
                f"DB: '{assignee.name}', Payload: '{task_data.final_assignee_name}'. "
                "Proceeding with email match."
            )

        db_task = self.task_repo.create_task_from_webhook(task_data, assignee.id)
        return db_task

    def update_task_status(self, task_id: int, task_update: TaskUpdate) -> TaskSchema:
        """ Task 정보 수정 """
        db_task = self.task_repo.update_task(task_id, task_update)
        if not db_task:
            logger.warning(f"Failed to update task. Task not found for ID: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")
        return db_task