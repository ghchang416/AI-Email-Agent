from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from db.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    department = Column(String)
    
    status = Column(String, default="업무 중") 
    
    tasks = relationship("Task", back_populates="assignee")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    
    sender_name = Column(String)
    sender_email = Column(String)
    received_mail_content = Column(Text)
    message_id = Column(String, index=True)
    
    draft_content = Column(Text)
    
    status = Column(String, default="시작 전")
    
    assignee_id = Column(Integer, ForeignKey("users.id"))
    
    assignee = relationship("User", back_populates="tasks")