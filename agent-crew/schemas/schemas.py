from pydantic import BaseModel, Field
from typing import Literal, Optional

class EmailAnalysis(BaseModel):
    category: Literal["TASK", "Directory_Inquiry", "OTHER"] = Field(description="분석된 이메일의 3가지 카테고리 (업무, 단순 질의, 기타)")
    summary: str = Field(description="이메일의 핵심 요약. 'OTHER' 카테고리일 경우 'N/A' 반환.")
    reasoning: str = Field(description="왜 이 카테고리로 분류했는지에 대한 간단한 근거.")
    