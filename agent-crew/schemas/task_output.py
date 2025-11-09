from pydantic import BaseModel, Field
from typing import Literal

class EmailAnalysis(BaseModel):
    category: Literal["TASK", "Directory_Inquiry", "OTHER"] = Field(description="분석된 이메일의 3가지 카테고리 (업무, 단순 질의, 기타)")
    summary: str = Field(description="이메일의 핵심 요약. 'OTHER' 카테고리일 경우 'N/A' 반환.")
    reasoning: str = Field(description="왜 이 카테고리로 분류했는지에 대한 간단한 근거.")
    
class RoutingResult(BaseModel):
    """라우팅 크루의 최종 출력을 위한 Pydantic 모델"""
    recipient_name: str = Field(..., description="찾아낸 담당자 이름")
    recipient_email: str = Field(..., description="찾아낸 담당자 이메일")

class DraftValidation(BaseModel):
    """LLM-as-a-Judge의 검증 결과를 담는 스키마"""
    passed: bool = Field(..., description="검증 기준(사실성, 관련성)을 통과했는지 여부 (True/False)")
    factuality_score: float = Field(..., description="사실성 점수 (0.0 ~ 1.0)")
    relevance_score: float = Field(..., description="관련성 점수 (0.0 ~ 1.0)")
    tone_score: float = Field(..., description="표현(어조) 점수 (0.0 ~ 1.0)")
    critique: str = Field(..., description="검증 기준 미달 시, 수정이 필요한 부분에 대한 구체적인 비평")