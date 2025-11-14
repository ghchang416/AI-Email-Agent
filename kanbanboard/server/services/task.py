import os
import logging
import requests
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
    N8N_COMPLETION_WEBHOOK_URL = os.getenv(
        "N8N_COMPLETION_WEBHOOK_URL", 
        "http://n8n:5678/webhook/fe6bff88-b878-4abf-aa5e-3cae3a117f8d"
    )
    
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
    
    def send_n8n_webhook_sync(self, message_id: str, content: str, assignee_name: str, user_email: str):
        """
        백그라운드에서 n8n 웹훅을 동기적으로 호출합니다.
        (BackgroundTasks는 비동기(async) 함수를 직접 지원하지 않으므로 동기 함수로 만듭니다.)
        """
        if not message_id:
            print("n8n Webhook: message_id가 없어 알림을 생략합니다.")
            return
        
        final_content = content

        if assignee_name and user_email:
            # 메일 본문(content) 밑에 담당자 서명 추가
            signature = f"\n\n---\n담당자: {assignee_name} {user_email}"
            final_content = content + signature

        try:
            payload = {"message_id": message_id, "content": final_content}
            response = requests.post(self.N8N_COMPLETION_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            print(f"n8n Webhook: {message_id} 알림 성공")
        except requests.exceptions.RequestException as e:
            print(f"[CRITICAL] n8n Webhook: {message_id} 알림 실패: {e}")
            pass