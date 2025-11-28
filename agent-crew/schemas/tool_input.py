from typing import Optional
from pydantic import BaseModel, Field

class SearchInternalDocsInput(BaseModel):
    """사내 문서 검색 도구의 입력 모델"""
    query: str = Field(..., description="답변 초안 작성을 위해 검색할 이메일 문의의 핵심 내용")
    source_file: str = Field(description="검색 대상을 한정할 정확한 파일명 (예: '2025학년도_소프트웨어융합대학_소프트웨어학과.pdf')")
    
class AdaptiveRagInput(BaseModel):
    """
    지능형 RAG 검색 도구 입력
    사용자의 이메일 본문을 그대로 입력받아, 내부적으로 최적의 파일과 쿼리를 찾아 검색합니다.
    """
    email: str = Field(..., description="정보 검색이 필요한 사용자의 이메일 본문 원문")    

class KanbanStatusInput(BaseModel):
    assignee_email: str = Field(..., description="상태를 조회할 담당자의 이메일 주소")
    
class SendKanbanTaskInput(BaseModel):
    """칸반 작업 전송 도구의 입력 스키마"""
    message_id: str = Field(description="원본 이메일의 메시지 ID")
    sender: str = Field(description="원본 이메일 발신자 주소")
    subject: str = Field(description="원본 이메일 제목")
    body: str = Field(description="원본 이메일 본문 전체")
    final_draft: Optional[str] = Field(description="AI가 생성한 답장 초안. 작성이 실패했을 경우 None일 수 있음")
    assignee_name: str = Field(description="최종 배정된 담당자 성명")
    assignee_email: str = Field(description="최종 배정된 담당자 이메일 주소")