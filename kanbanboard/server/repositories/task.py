from sqlalchemy.orm import Session
from db.models import Task
from schemas.task import KanbanTaskCreateSchema, TaskUpdate
from typing import List, Optional

class TaskRepository:
    """ Task 모델에 대한 데이터베이스 CRUD 연산을 담당합니다. """

    def __init__(self, db: Session):
        self.db = db
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """ ID로 Task 1개 조회 """
        return self.db.query(Task).filter(Task.id == task_id).first()

    def get_tasks_by_assignee(self, assignee_id: int) -> List[Task]:
        """ 특정 담당자의 모든 Task 조회 """
        return self.db.query(Task).filter(Task.assignee_id == assignee_id).all()

    def get_all_tasks(self) -> List[Task]:
        """ 모든 Task 조회 """
        return self.db.query(Task).all()

    def create_task_from_webhook(
        self, 
        task_data: KanbanTaskCreateSchema, 
        assignee_id: int
    ) -> Task:
        """
        [핵심] Webhook 페이로드(task_data)와 확정된 assignee_id를 받아
        새로운 Task 레코드를 생성합니다.
        """
        db_task = Task(
            title=f"Re: {task_data.original_subject}",
            status="시작 전", 
            assignee_id=assignee_id,
            
            sender_name=task_data.original_sender,
            sender_email=task_data.original_sender,
            
            received_mail_content=task_data.original_body,
            message_id=task_data.message_id,
            draft_content=task_data.ai_drafted_reply
        )
        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def update_task(self, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
        """ Task 정보 수정 (예: 칸반보드에서 상태 변경 시) """
        db_task = self.get_task_by_id(task_id)
        if db_task:
            update_data = task_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_task, key, value)
            self.db.commit()
            self.db.refresh(db_task)
        return db_task

    def get_active_task_count_by_user(self, user_id: int) -> int:
        """ 특정 사용자의 '완료'되지 않은 작업 수를 계산합니다. """
        return self.db.query(Task).filter(
            Task.assignee_id == user_id, 
            Task.status != "완료"
        ).count()