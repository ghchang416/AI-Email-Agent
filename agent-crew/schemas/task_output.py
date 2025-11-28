from pydantic import BaseModel, Field
from typing import Literal, List, Optional

class EmailAnalysis(BaseModel):
    category: Literal["TASK", "Simple_Inquiry", "OTHER"] = Field(description="분석된 이메일의 3가지 카테고리 (업무, 단순 질의, 기타)")
    summary: str = Field(description="이메일의 핵심 요약. 'OTHER' 카테고리일 경우 'N/A' 반환.")
    reasoning: str = Field(description="왜 이 카테고리로 분류했는지에 대한 간단한 근거.")
    
class RoutingResult(BaseModel):
    recipient_name: str = Field(..., description="담당자 이름")
    recipient_email: str = Field(..., description="담당자 이메일")
    matched_duty_description: str = Field(..., description="매칭된 업무 설명")
    duty_validation_reasoning: str = Field(..., description="업무 일치 근거")
    confidence_score: int = Field(..., description="확신도 (0~100)")

class FinalAssigneeResult(BaseModel):
    """ 최종 담당자 확정 결과 (종합 검증)"""
    final_assignee_name: str = Field(description="최종 검증 대상 담당자 이름")
    final_assignee_email: str = Field(description="최종 검증 대상 담당자 이메일")
    status: Literal['Success', 'Failed'] = Field(description="최종 담당자 확정 상태 ('Success' 또는 'Failed')")
    reasoning: str = Field(description="확정 또는 실패 사유 (예: '업무 일치 및 스케줄 가용' 또는 '업무 불일치' 또는 '스케줄 검증 실패: 휴가 중')")

class DraftOutput(BaseModel):
    status: Literal["COMPLETED", "NEEDS_INFO"] = Field(..., description="작성 완료 여부")
    draft_content: Optional[str] = Field(description="완성된(또는 수정된) 이메일 초안 (COMPLETED일 때)")
    missing_info_query: Optional[str] = Field(description="필요한 타 부서 정보에 대한 질문 (NEEDS_INFO일 때)")
    target_dept_hint: Optional[str] = Field(description="정보를 알 것 같은 부서 힌트")
    
class DraftValidation(DraftOutput):
    """LLM-as-a-Judge의 검증 결과"""
    passed: bool = Field(..., description="검증 통과 여부 (사실성/관련성/어조 기준)")
    factuality_score: float = Field(..., description="사실성 점수 (0.0 ~ 1.0). 제공된 Context에 기반했는지 여부")
    relevance_score: float = Field(..., description="관련성 점수 (0.0 ~ 1.0). 질문에 동문서답하지 않았는지 여부")
    tone_score: float = Field(..., description="표현(어조) 점수 (0.0 ~ 1.0). 정중하고 전문적인지 여부")
    critique: str = Field(..., description="점수에 대한 비평 및 수정이 필요한 부분")

class DepartmentRoutingDecision(BaseModel):
    primary_dept_id: str = Field(..., description="목록에서 가장 적절한 주관 부서 ID를 선택합니다. 일치하는 부서가 없거나 스팸인 경우 'OTHER'를 선택하세요.")
    is_spam: bool = Field(default=False, description="이메일이 스팸이거나 대학 행정 업무와 무관한 경우 True입니다.")

class SupportingDeptDecision(BaseModel):
    dept_id: Optional[str] = Field(None, description="해당 문의에 답변할 수 있는 부서 ID입니다. 찾을 수 없는 경우 None을 반환합니다.")    
    
class RagPlan(BaseModel):
    target_filename: str = Field(..., description="검색할 PDF 파일명")
    search_queries: List[str] = Field(..., description="검색 쿼리 3개")