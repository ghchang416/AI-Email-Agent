import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.user import router as user_router
from routers.task import router as task_router
from db.session import create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kanban API for CrewAI",
    description="This API manages users and tasks for the email automation crew.",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """
    애플리케이션이 시작될 때 한 번 실행됩니다.
    - DB 테이블을 생성합니다.
    - 초기 데이터가 없으면 삽입합니다.
    """
    create_tables() # db/session.py


app.include_router(user_router)
app.include_router(task_router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Kanban API. Visit /docs for API documentation."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8888, reload=True)