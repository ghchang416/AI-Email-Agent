import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../..", "data")
DB_DIR = os.path.join(BASE_DIR, "../..", "chroma_db")

ORG_CHART_JSON_PATH = os.path.join(DATA_DIR, "업무분장표/소프트웨어융합대학_업무분장표.json")

CHROMA_DB_PATH = DB_DIR
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"
VECTOR_DB_K = 3


N8N_SEND_REPLY_WEBHOOK_URL = "http://localhost:5678/webhook/7c48c472-33c8-409b-bbcf-7fff85c548f1"
N8N_SPAM_PROCESS_WEBHOOK_URL = "http://localhost:5678/webhook/11091293-d689-408a-854d-803fdf6d41cf"
N8N_GET_USER_STATUS_WEBHOOK_URL = "http://localhost:8888/users/status-by-email"
N8N_CREATE_KANBAN_TASK_WEBHOOK_URL = "http://localhost:8888/tasks"

DEFAULT_MANAGER_NAME = "총괄 담당자"
DEFAULT_MANAGER_EMAIL = "manager@ajou.ac.kr"