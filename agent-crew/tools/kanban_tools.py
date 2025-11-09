import json
import requests
import logging
from typing import Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel
from schemas.tool_input import KanbanStatusInput, SendKanbanTaskInput
from utils import config

logger = logging.getLogger(__name__)

class GetKanbanUserStatusTool(BaseTool):
    name: str = "칸반 보드 사용자 상태 조회 도구"
    description: str = "담당자의 이메일을 받아, 현재 칸반 보드 상의 상태(휴가, 업무량)를 반환합니다."
    args_schema: Type[BaseModel] = KanbanStatusInput
    
    def __init__(self):
        self.webhook_url = config.N8N_GET_USER_STATUS_WEBHOOK_URL
        
    def _run(self, assignee_email: str) -> str:
        """ Kanban Board 서버를 호출하여 담당자 상태를 가져옵니다. """
        params = {'email': assignee_email}
        try:
            response = requests.get(self.webhook_url, params=params, timeout=5)
            response.raise_for_status() 
        
            status_data = response.json()
            logger.info(f"Status received for {assignee_email}: {status_data.get('status')}")
            return json.dumps(status_data)

        except Exception as e:
            logger.error(f"Error fetching status for {assignee_email}: {str(e)}", exc_info=True)
            return json.dumps({
                "error": "Failed to fetch user status",
                "email": assignee_email,
                "details": str(e)
            })
            
class SendTaskToKanbanTool(BaseTool):
    name: str = "칸반보드 서버로 완성된 메일 작업 송신"
    description: str = (
        "최종 'TASK' 세부 정보(이메일, AI 초안, 최종 담당자)를 보냅니다"
        "칸반보드 서버의 웹훅을 통해 새로운 작업 카드를 만듭니다"
    )
    args_schema: Type[BaseModel] = SendKanbanTaskInput
    
    def _run(
        self, 
        message_id: str,
        sender: str,
        subject: str,
        body: str,
        assignee_name: str,
        assignee_email: str,
        final_draft: Optional[str] = None
    ) -> str:
        """
        n8n 웹훅을 호출하여 칸반 카드 생성을 요청합니다.
        성공 시: "Success: [메시지]"
        실패 시: "Error: [에러 상세]"
        """
        
        try:
            webhook_url = config.N8N_CREATE_KANBAN_TASK_WEBHOOK_URL
        except AttributeError:
            logger.critical("[Tool Error] 'N8N_CREATE_KANBAN_TASK_WEBHOOK_URL' not set in config.py.")
            return "Error: Tool configuration error. The Kanban webhook URL is not set."

        payload = {
            "message_id": message_id,
            "original_sender": sender,
            "original_subject": subject,
            "original_body": body,
            "ai_drafted_reply": final_draft,
            "final_assignee_name": assignee_name,
            "final_assignee_email": assignee_email
        }
        
        logger.info(f"Sending 'TASK' data to Kanban webhook for assignee: {assignee_email}")

        try:
            response = requests.post(webhook_url, json=payload, timeout=10) 
            response.raise_for_status() 
            
            logger.info(f"Successfully sent task to Kanban for message_id: {message_id}")
            return f"Success: The task for '{subject}' was successfully sent to the Kanban board and assigned to {assignee_name}."
        except Exception as e:
            logger.error(f"Failed to send task to Kanban (General Request Error): {e}", exc_info=True)
            return f"Error: A general network error occurred. Details: {e}"