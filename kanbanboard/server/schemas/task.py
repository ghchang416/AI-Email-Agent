from pydantic import BaseModel
from typing import Optional

class TaskSchemaBase(BaseModel):
    title: str
    status: str
    assignee_id: int
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    received_mail_content: Optional[str] = None
    message_id: Optional[str] = None
    draft_content: Optional[str] = None


class KanbanTaskCreateSchema(BaseModel):
    message_id: str
    original_sender: str
    original_subject: str
    original_body: str
    ai_drafted_reply: Optional[str]
    final_assignee_name: str
    final_assignee_email: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    received_mail_content: Optional[str] = None
    message_id: Optional[str] = None
    draft_content: Optional[str] = None

class TaskSchema(TaskSchemaBase):
    id: int
    
    class Config:
        from_attributes = True