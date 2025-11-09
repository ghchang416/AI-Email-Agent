from pydantic import BaseModel, Field

class SearchInternalDocsInput(BaseModel):
    """사내 문서 검색 도구의 입력 모델"""
    query: str = Field(..., description="답변 초안 작성을 위해 검색할 이메일 문의의 핵심 내용")