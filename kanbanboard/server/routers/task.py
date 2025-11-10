from fastapi import APIRouter, Depends, BackgroundTasks
from typing import List, Optional
from schemas.task import TaskSchema, KanbanTaskCreateSchema, TaskUpdate
from services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("", response_model=List[TaskSchema], summary="모든 Task 조회 (담당자 필터링)")
async def get_all_tasks(
    assignee_id: Optional[int] = None, # 쿼리 파라미터 (예: /tasks?assignee_id=1)
    service: TaskService = Depends()
):
    """ 
    모든 작업을 조회하거나, 'assignee_id' 쿼리 파라미터를 제공하여
    특정 담당자에게 배정된 작업만 필터링합니다. 
    """
    return service.get_tasks_for_assignee(assignee_id)

@router.post("", response_model=TaskSchema, status_code=201, summary="[For CrewAI] 새 Task 생성 (Webhook)")
async def create_new_task(
    task_data: KanbanTaskCreateSchema,
    service: TaskService = Depends()
):
    """
    CrewAI의 SendTaskToKanbanTool이 호출하는 엔드포인트입니다.
    Webhook 페이로드(이메일 원본, 초안, 담당자 이메일)를 받아
    새로운 Task를 생성하고 DB에 저장합니다.
    """
    return service.create_task_from_webhook_payload(task_data)

@router.put("/{task_id}", response_model=TaskSchema, summary="Task 정보 수정")
async def update_existing_task(
    task_id: int, 
    task_update: TaskUpdate, 
    background_tasks: BackgroundTasks,
    service: TaskService = Depends(),
):
    """ Task의 상태, 담당자, 내용 등을 수정합니다. """
    if task_update.status == "완료":
        background_tasks.add_task(
            service.send_n8n_webhook_sync,
            task_update.message_id, 
            task_update.draft_content
        )
    return service.update_task_status(task_id, task_update)