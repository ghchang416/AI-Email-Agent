from tools.rag_tools import SearchOrgChartTool, SearchInternalDocsTool, ListKnowledgeBaseFilesTool
from tools.kanban_tools import GetKanbanUserStatusTool, SendTaskToKanbanTool

search_org_chart_tool = SearchOrgChartTool()
search_internal_docs_tool = SearchInternalDocsTool()
list_knowledge_base_file_tool = ListKnowledgeBaseFilesTool()
get_kanban_user_status_tool = GetKanbanUserStatusTool()
send_task_to_kanban_tool = SendTaskToKanbanTool()