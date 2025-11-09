from fastapi import APIRouter, Depends
from typing import List
from schemas.user import UserSchema, UserUpdate, KanbanUserStatusSchema, UserCreate
from services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=List[UserSchema], summary="모든 사용자 조회")
async def get_all_users(
    service: UserService = Depends()
):
    """ 모든 사용자의 목록을 반환합니다. """
    return service.get_all_users()

@router.post("", response_model=UserSchema, status_code=201, summary="새 사용자 생성")
async def create_new_user(
    user_data: UserCreate,
    service: UserService = Depends()
):
    """
    새로운 사용자를 생성합니다. (Streamlit data_editor의 '행 추가' 기능용)
    이메일이 중복될 경우 409 Conflict 에러를 반환합니다.
    """
    return service.create_new_user(user_data)

@router.get(
    "/status-by-email", 
    response_model=KanbanUserStatusSchema, 
    summary="[For CrewAI] 이메일로 사용자 상태 및 업무량 조회"
)
async def get_user_status_by_email(
    email: str, # 쿼리 파라미터 (예: /status-by-email?email=user@example.com)
    service: UserService = Depends()
):
    """
    이메일 주소를 받아, 사용자의 현재 상태('휴가 중' 등)와
    활성 작업 수를 분석하여 최종 가용 상태('Available', 'Vacation', 'Overloaded')를 반환합니다.
    """
    return service.get_user_status_for_kanban(email)

@router.get("/{user_id}", response_model=UserSchema, summary="특정 사용자 ID로 조회")
async def get_user_by_id(
    user_id: int, 
    service: UserService = Depends()
):
    """ ID에 해당하는 사용자의 상세 정보를 반환합니다. """
    return service.get_user_by_id(user_id)

@router.put("/{user_id}", response_model=UserSchema, summary="사용자 정보 수정")
async def update_user_details(
    user_id: int, 
    user_update: UserUpdate, 
    service: UserService = Depends()
):
    """ 사용자의 정보(이름, 이메일, 상태 등)를 수정합니다. """
    return service.update_user_status(user_id, user_update)