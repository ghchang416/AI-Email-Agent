from tools.rag_tools import SearchOrgChartTool, AdaptiveRagSearchTool
from tools.kanban_tools import GetKanbanUserStatusTool, SendTaskToKanbanTool

search_org_chart_tool = SearchOrgChartTool()
adaptive_rag_search_tool = AdaptiveRagSearchTool()

get_kanban_user_status_tool = GetKanbanUserStatusTool()
send_task_to_kanban_tool = SendTaskToKanbanTool()