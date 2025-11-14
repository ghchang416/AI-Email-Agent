import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, PrivateAttr
from langchain_community.vectorstores import Chroma
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
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
    
    _staff_data: list = PrivateAttr(default=None)
    _minio_bucket: str = PrivateAttr()
    _minio_object_key: str = PrivateAttr()
    _minio_endpoint_url: str = PrivateAttr()
    _minio_access_key: str = PrivateAttr()
    _minio_secret_key: str = PrivateAttr()
    _s3_client = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        """
        도구 초기화 시 MinIO 클라이언트 설정을 환경 변수에서 로드합니다.
        """
        super().__init__(**kwargs)
        
        self._minio_bucket = os.getenv("MINIO_BUCKET", "academic-bucket")
        self._minio_object_key = os.getenv("ORG_CHART_JSON_KEY", "software_org_chart.json")
        self._minio_endpoint_url = os.getenv("MINIO_ENDPOINT_URL", "http://minio:9000")
        self._minio_access_key = os.getenv("MINIO_ACCESS_KEY", "ajou")
        self._minio_secret_key = os.getenv("MINIO_SECRET_KEY", "software")

        try:
            self._s3_client = boto3.client(
                's3',
                endpoint_url=self._minio_endpoint_url,
                aws_access_key_id=self._minio_access_key,
                aws_secret_access_key=self._minio_secret_key,
                use_ssl=False
            )
            # 버킷 존재 여부 확인으로 연결 테스트
            self._s3_client.head_bucket(Bucket=self._minio_bucket)
            logger.info(f"[OrgChartTool] MinIO client initialized successfully. Bucket: '{self._minio_bucket}'")
        except Exception as e:
            logger.error(f"[OrgChartTool] Failed to initialize MinIO client: {e}", exc_info=True)
            self._s3_client = None

    def _load_data(self) -> list:
        """
        MinIO에서 조직도 JSON 파일을 다운로드하고 파싱하여 캐시합니다.
        """
        if self._staff_data is not None:
            logger.debug("Returning cached organization chart data.")
            return self._staff_data

        if self._s3_client is None:
            logger.error("[OrgChartTool] MinIO client is not initialized. Cannot load data.")
            raise OrgChartToolError("MinIO client failed to initialize. Check logs.")

        logger.info(f"Cache miss. Loading organization chart from MinIO: s3://{self._minio_bucket}/{self._minio_object_key}")
        
        try:
            response = self._s3_client.get_object(
                Bucket=self._minio_bucket, 
                Key=self._minio_object_key
            )
            
            file_content = response['Body'].read().decode('utf-8')
            data = json.loads(file_content)
            
            self._staff_data = data["업무분장표"]
            logger.info("Successfully loaded and cached organization chart from MinIO.")

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.error(f"[Tool Error] File not found in MinIO: s3://{self._minio_bucket}/{self._minio_object_key}")
                raise OrgChartToolError(f"File not found in MinIO: {self._minio_object_key}") from e
            else:
                logger.error(f"[Tool Error] MinIO ClientError: {e}", exc_info=True)
                raise OrgChartToolError(f"MinIO access error: {e}") from e
        except Exception as e:
            logger.error(f"[Tool Error] Unexpected error loading data from MinIO: {e}", exc_info=True)
            raise OrgChartToolError(f"An unexpected error occurred while reading from MinIO: {e}") from e

        return self._staff_data

    def _run(self) -> str:
        try:
            staff_list = self._load_data()

            if not staff_list:
                logger.warning("Organization chart data is available but empty.")
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
    _chroma_host: str = PrivateAttr()
    _chroma_port: int = PrivateAttr()
    _collection_name: str = PrivateAttr()
    _embedding_model: str = PrivateAttr()
    _search_k: int = PrivateAttr()
    _device_type: str = PrivateAttr()

    def __init__(self, **kwargs):
        """
        도구 초기화 시 벡터 DB와 임베딩 모델을 로드합니다. (os.getenv 사용)
        """
        super().__init__(**kwargs)
        
        logger.info("[RAG Tool] Initializing Vector DB and Retriever...")

        self._chroma_host = os.getenv("CHROMA_HOST", "chromadb")
        self._chroma_port = int(os.getenv("CHROMA_PORT", 8000))
        self._collection_name = os.getenv("CHROMA__COLLECTION_NAME", "academic_regulations")
        self._embedding_model = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
        self._search_k = int(os.getenv("VECTOR_DB_K", 3))
        self._device_type = os.getenv("DEVICE_TYPE", "cpu")

        if not all([self._chroma_host, self._chroma_port, self._collection_name, self._embedding_model]):
            logger.critical("[RAG Tool Error] ChromaDB server configuration is missing from environment variables.")
            return

        try:
            logger.info(f"Loading embedding model: {self._embedding_model} (Device: {self._device_type})")
            model_kwargs = {'device': self._device_type}
            encode_kwargs = {'normalize_embeddings': True}
            embeddings = HuggingFaceEmbeddings(
                model_name=self._embedding_model,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
            
            logger.info(f"Connecting to Vector DB Server at: {self._chroma_host}:{self._chroma_port}")
            
            client = chromadb.HttpClient(
                host=self._chroma_host, 
                port=self._chroma_port
            )
            
            self._vectorstore = Chroma(
                client=client,
                collection_name=self._collection_name,
                embedding_function=embeddings
            )
            
            self._retriever = self._vectorstore.as_retriever(search_kwargs={"k": self._search_k})
            
            logger.info(f"[RAG Tool] Vector DB and Retriever loaded successfully (k={self._search_k}).")
            
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
                context += "\n\S"
            
            context += "--- [End of Search Results] ---"
            
            logger.info(f"[RAG Tool] Search complete. Returning {len(docs)} fragments.")
            return context
            
        except Exception as e:
            logger.error(f"[RAG Tool] Error during search invocation for query '{query}': {e}", exc_info=True)
            return f"Error: An exception occurred during the RAG search. Details: {e}"