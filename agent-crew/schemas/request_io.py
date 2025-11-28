from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from schemas.task_output import EmailAnalysis, FinalAssigneeResult

class EmailInput(BaseModel):
    message_id: str = Field(description="Gmail의 고유 메시지 ID")
    sender: str = Field(description="이메일 보낸 사람")
    subject: str = Field(description="이메일 제목")
    body: str = Field(description="이메일 본문")
    
class EmailFlowState(BaseModel):
    email_data: Optional[EmailInput] = Field(None, description="처리할 원본 이메일 입력 데이터")       
    analysis_result: Optional[EmailAnalysis] = Field(None, description="LLM을 통한 이메일 분석 결과 (요약, 의도, 키워드 등)")
    routing_decision: Optional[Dict[str, Any]] = Field(None, description="부서 라우팅 및 스팸 분류 결정 정보")
    final_assignee_result: Optional[FinalAssigneeResult] = Field(None, description="최종적으로 배정된 담당자 및 부서 정보")
    logs: List[str] = Field(default=[], description="워크플로우 실행 중 발생한 주요 로그 리스트")
    
    current_context: str = Field(default="", description="현재까지 수집된 부서별 정보 누적 텍스트")
    retry_count: int = Field(default=0, description="정보 부족으로 인한 재시도(루프) 횟수")
    target_dept_id: Optional[str] = Field(default=None, description="현재 단계에서 정보를 수집해야 할 목표 부서 ID (초기는 주관부서, 이후는 협조부서)")
    search_query: Optional[str] = Field(default=None, description="현재 단계에서 해당 부서에 질의할 내용")
    draft_status: str = Field(default="PENDING", description="초안 작성 상태 (PENDING, COMPLETED, NEEDS_INFO)")