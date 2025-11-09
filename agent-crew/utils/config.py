import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../..", "data")
DB_DIR = os.path.join(BASE_DIR, "../..", "chroma_db")

ORG_CHART_JSON_PATH = os.path.join(DATA_DIR, "업무분장표/소프트웨어융합대학.json")

CHROMA_DB_PATH = DB_DIR
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"
VECTOR_DB_K = 3