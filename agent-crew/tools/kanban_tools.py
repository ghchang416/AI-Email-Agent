import json
import requests
import logging
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel
from schemas.tool_input import KanbanStatusInput
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