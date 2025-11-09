from pydantic import BaseModel, Field

class EmailInput(BaseModel):
    message_id: str = Field(description="Gmail의 고유 메시지 ID")
    sender: str = Field(description="이메일 보낸 사람")
    subject: str = Field(description="이메일 제목")
    body: str = Field(description="이메일 본문")