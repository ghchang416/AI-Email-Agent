import json
import logging
from crewai.tools import BaseTool
from pydantic import PrivateAttr
from utils import config
from utils.exceptions import OrgChartToolError

logger = logging.getLogger(__name__)

class SearchOrgChartTool(BaseTool):
    name: str = "조직도 및 업무 분장표 로드 도구"
    description: str = (
        "업무분장표 파일 전체 내용을 JSON 문자열로 불러옵니다. "
        "입력(query)은 필요하지 않습니다. "
        "에이전트는 이 전체 텍스트 내용을 바탕으로 필요한 담당자 정보를 직접 찾아야 합니다."
    )

    json_file_path: str = config.ORG_CHART_JSON_PATH
    _staff_data: list = PrivateAttr(default=None)

    def _load_data(self) -> list:
        if self._staff_data is None:
            logger.info(f"Cache miss. Loading organization chart from: {self.json_file_path}")
            try:
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._staff_data = data["업무분장표"]
                
                logger.info(f"Successfully loaded and cached data for '{self.json_file_path}'.")

            except FileNotFoundError as e:
                logger.error(f"[Tool Error] Configuration error: File not found at {self.json_file_path}")
                raise OrgChartToolError(f"File not found: {self.json_file_path}") from e

            except Exception as e:
                logger.error(f"[Tool Error] Unexpected error loading file: {e}", exc_info=True)
                raise OrgChartToolError(f"An unexpected error occurred while reading the file: {e}") from e

        return self._staff_data

    def _run(self) -> str:
        try:
            staff_list = self._load_data()

            if not staff_list:
                logger.warning(f"Organization chart data is available but empty for {self.json_file_path}.")
                return "Warning: Organization chart data is available but currently empty."

            return json.dumps(staff_list, indent=2, ensure_ascii=False)

        except OrgChartToolError as e:
            logger.error(f"Failed to provide org chart data to agent. Error: {e}")
            return f"Error: Failed to load organization chart data. Details: {e}"
        
        except Exception as e:
            logger.error(f"[Tool Error] Unexpected error in _run method: {e}", exc_info=True)
            return f"Error: An unexpected internal error occurred in the tool. Details: {e}"