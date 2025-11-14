from typing import Optional
from pydantic import BaseModel, Field

class SearchInternalDocsInput(BaseModel):
    """사내 문서 검색 도구의 입력 모델"""
    query: str = Field(..., description="답변 초안 작성을 위해 검색할 이메일 문의의 핵심 내용")
    source_file: str = Field(description="검색 대상을 한정할 정확한 파일명 (예: '2025학년도_소프트웨어융합대학_소프트웨어학과.pdf')")
    
class KanbanStatusInput(BaseModel):
    assignee_email: str = Field(..., description="상태를 조회할 담당자의 이메일 주소")
    
class SendKanbanTaskInput(BaseModel):
    """칸반 작업 전송 도구의 입력 스키마"""
    message_id: str = Field(description="Original email message ID.")
    sender: str = Field(description="Original email sender's address.")
    subject: str = Field(description="Original email subject line.")
    body: str = Field(description="Original email full body text.")
    final_draft: Optional[str] = Field(description="The AI-generated reply draft. Can be None if drafting failed.")
    assignee_name: str = Field(description="The full name of the final assigned staff member.")
    assignee_email: str = Field(description="The email address of the final assigned staff member.")