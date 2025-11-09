from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

class UserSchemaBase(BaseModel):
    name: str
    email: EmailStr
    department: Optional[str] = None
    status: str

class UserCreate(UserSchemaBase):
    pass

class UserUpdate(UserSchemaBase):
    pass

class UserSchema(UserSchemaBase):
    id: int

    class Config:
        from_attributes = True

class KanbanUserStatusSchema(BaseModel):
    email: EmailStr
    status: Literal['Available', 'Vacation', 'Overloaded']
    message: str 
    active_task_count: int
    raw_db_status: str