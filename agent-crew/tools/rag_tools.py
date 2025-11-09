import json
import logging
import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, PrivateAttr
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from utils import config
from utils.exceptions import OrgChartToolError
from schemas.tool_input import SearchInternalDocsInput

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

class SearchInternalDocsTool(BaseTool):
    name: str = "사내 규정 및 FAQ 검색 도구 (RAG)"
    description: str = (
        "답변 초안 작성에 필요한 정보를 '학사 요람' 규정, FAQ 등에서 RAG 기반으로 검색합니다."
    )
    args_schema: Type[BaseModel] = SearchInternalDocsInput
    
    _vectorstore: Chroma = PrivateAttr(default=None)
    _retriever = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        """
        도구 초기화 시 벡터 DB와 임베딩 모델을 로드합니다.
        """
        super().__init__(**kwargs)
        
        logger.info("[RAG Tool] Initializing Vector DB and Retriever...")

        if not config.CHROMA_DB_PATH or not config.EMBEDDING_MODEL:
            logger.critical("[RAG Tool Error] CHROMA_DB_PATH or EMBEDDING_MODEL is not set in config.")
            return

        if not os.path.exists(config.CHROMA_DB_PATH):
            logger.critical(f"[RAG Tool Error] Vector DB path not found: '{config.CHROMA_DB_PATH}'")
            logger.critical("Please run the data ingestion script first (e.g., ingest_pdfs.py).")
            return

        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            model_kwargs = {'device': 'cpu'}
            encode_kwargs = {'normalize_embeddings': True}
            embeddings = HuggingFaceEmbeddings(
                model_name=config.EMBEDDING_MODEL,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
            
            logger.info(f"Loading Vector DB from: {config.CHROMA_DB_PATH}")
            self._vectorstore = Chroma(
                persist_directory=config.CHROMA_DB_PATH, 
                embedding_function=embeddings
            )
            
            search_k = getattr(config, 'VECTOR_DB_K', 3)
            self._retriever = self._vectorstore.as_retriever(search_kwargs={"k": search_k})
            
            logger.info(f"[RAG Tool] Vector DB and Retriever loaded successfully (k={search_k}).")
            
        except Exception as e:
            logger.error(f"[RAG Tool Error] Failed to load Vector DB during initialization: {e}", exc_info=True)

    def _run(self, query: str) -> str:
        """
        에이전트가 도구를 실행할 때 호출되는 함수
        """
        if self._retriever is None:
            logger.error("[RAG Tool Error] _run called, but tool is not initialized. Check initialization logs.")
            return "Error: RAG tool is not initialized. Check system logs for errors (e.g., DB path, model name)."

        logger.info(f"[RAG Tool] Executing search for query: '{query}'")
        
        try:
            docs = self._retriever.invoke(query)
            
            if not docs:
                logger.warning(f"▶️ [RAG Tool] No documents found for query: '{query}'")
                return "Info: No relevant academic regulations or documents were found for this query."

            context = "--- [Reference: RAG Search Results] ---\n\n"
            for i, doc in enumerate(docs):
                source = os.path.basename(doc.metadata.get('source', 'N/A'))
                context += f"Fragment {i+1} (Source: {source}):\n"
                context += doc.page_content
                context += "\n\n"
            
            context += "--- [End of Search Results] ---"
            
            logger.info(f"[RAG Tool] Search complete. Returning {len(docs)} fragments.")
            return context
            
        except Exception as e:
            logger.error(f"[RAG Tool] Error during search invocation for query '{query}': {e}", exc_info=True)
            return f"Error: An exception occurred during the RAG search. Details: {e}"
        
