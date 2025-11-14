import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
from typing import Type, List
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

class ListKnowledgeBaseFilesTool(BaseTool):
    """
    RAG DB에 저장된 모든 고유한 'source' 파일명 목록을 조회하는 도구입니다.
    에이전트는 이 목록을 보고 어떤 파일을 필터링할지 결정해야 합니다.
    """
    name: str = "사용 가능한 RAG 문서 목록 조회"
    description: str = (
        "RAG 검색을 수행하기 전, DB에 어떤 파일(요람)이 있는지 전체 목록을 조회합니다. "
        "입력(query)은 필요하지 않습니다."
    )
    
    _client = PrivateAttr(default=None)
    _collection_name: str = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("[ListFilesTool] Initializing ChromaDB connection...")
        try:
            self._collection_name = os.getenv("CHROMA_COLLECTION_NAME", "academic_regulations")
            chroma_host = os.getenv("CHROMA_HOST", "chromadb")
            chroma_port = int(os.getenv("CHROMA_PORT", 8000))
            
            self._client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            # 컬렉션 존재 여부 테스트
            self._client.get_collection(name=self._collection_name) 
            logger.info("[ListFilesTool] Connection successful.")
        except Exception as e:
            logger.error(f"[ListFilesTool Error] Failed to connect to ChromaDB: {e}", exc_info=True)
            self._client = None

    def _run(self) -> List[str]:
        if self._client is None:
            return ["Error: ListFilesTool is not initialized. Check DB connection."]
            
        try:
            collection = self._client.get_collection(name=self._collection_name)
            data = collection.get(include=["metadatas"])
            
            metadatas = data.get('metadatas')
            if not metadatas:
                return ["Error: Collection is empty or metadatas are missing."]

            unique_sources = set()
            for meta in metadatas:
                source_file = meta.get('source')
                if source_file:
                    unique_sources.add(source_file)
            
            return sorted(list(unique_sources))
        
        except Exception as e:
            logger.error(f"[ListFilesTool Error] Failed to fetch metadata: {e}", exc_info=True)
            return [f"Error fetching metadata: {e}"]

class SearchInternalDocsTool(BaseTool):
    """
    특정 'source_file' 내부에서 'query'와 가장 유사한 청크 및
    그 앞/뒤 문맥을 함께 조회하는 RAG 도구입니다.
    """
    name: str = "사내 규정 및 FAQ 검색 도구 (RAG)"
    description: str = (
        "답변 초안 작성에 필요한 정보를 '학사 요람' 규정, FAQ 등에서 RAG 기반으로 검색합니다."
        "반드시 'query'와 'source_file'을 함께 제공해야 합니다."
    )
    args_schema: Type[BaseModel] = SearchInternalDocsInput
    
    _vectorstore: Chroma = PrivateAttr(default=None)
    _chroma_host: str = PrivateAttr()
    _chroma_port: int = PrivateAttr()
    _collection_name: str = PrivateAttr()
    _embedding_model: str = PrivateAttr()
    _search_k: int = PrivateAttr()
    _device_type: str = PrivateAttr()

    def __init__(self, **kwargs):
        """
        도구 초기화 시 벡터 DB와 임베딩 모델을 로드합니다.
        """
        super().__init__(**kwargs)
        
        logger.info("[RAG Tool] Initializing Vector DB...")

        self._chroma_host = os.getenv("CHROMA_HOST", "chromadb")
        self._chroma_port = int(os.getenv("CHROMA_PORT", 8000))
        # [오타 수정] CHROMA__COLLECTION_NAME -> CHROMA_COLLECTION_NAME
        self._collection_name = os.getenv("CHROMA_COLLECTION_NAME", "academic_regulations")
        self._embedding_model = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
        self._search_k = int(os.getenv("VECTOR_DB_K", 3)) # K=3으로 기본 설정
        self._device_type = os.getenv("DEVICE_TYPE", "cpu")

        if not all([self._chroma_host, self._chroma_port, self._collection_name, self._embedding_model]):
            logger.critical("[RAG Tool Error] ChromaDB server configuration is missing.")
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
            
            # [수정] LangChain 0.2.9+ 호환 (langchain-chroma 사용)
            self._vectorstore = Chroma(
                client=client,
                collection_name=self._collection_name,
                embedding_function=embeddings
            )
            
            # [수정] Retriever를 미리 만들지 않음 (필터가 동적이기 때문)
            logger.info(f"[RAG Tool] Vector DB connection successful (k={self._search_k}).")
            
        except Exception as e:
            logger.error(f"[RAG Tool Error] Failed to load Vector DB during initialization: {e}", exc_info=True)

    def _run(self, query: str, source_file: str) -> str:
        """
        에이전트가 도구를 실행할 때 호출되는 함수 (필터링 및 문맥 확장 수행)
        """
        if self._vectorstore is None:
            logger.error("[RAG Tool Error] _run called, but tool is not initialized.")
            return "Error: RAG tool is not initialized. Check system logs for errors."

        logger.info(f"[RAG Tool] Executing search for query: '{query}' with filter: '{source_file}'")
        
        try:
            # 1. 필터링된 유사도 검색 실행
            docs_with_scores = self._vectorstore.similarity_search_with_relevance_scores(
                query, 
                k=self._search_k,
                filter={"source": source_file} 
            )
            
            if not docs_with_scores:
                logger.warning(f"▶️ [RAG Tool] No documents found for query: '{query}' in file: '{source_file}'")
                return f"Info: '{source_file}' 파일 내에서 '{query}'와 관련된 문서를 찾지 못했습니다."

            # 2. 문맥 확장 (Context Expansion) - test_rag.py 로직 적용
            best_doc, best_score = docs_with_scores[0]
            best_meta = best_doc.metadata
            best_chunk_id_int = best_meta.get('chunk_id')

            full_context = ""
            
            if best_chunk_id_int is not None:
                # 2.1. 이 청크의 앞/뒤 ID를 계산
                prev_chunk_id_int = best_chunk_id_int - 1
                next_chunk_id_int = best_chunk_id_int + 1
                
                # 2.2. 'get' 메소드를 사용해 ID로 앞/뒤 청크를 직접 조회
                
                # --- 앞 청크 조회 ---
                prev_chunk_data = self._vectorstore.get(
                    where={"$and": [
                        {"source": source_file},
                        {"chunk_id": prev_chunk_id_int}
                    ]},
                    include=["documents"]
                )
                if prev_chunk_data and prev_chunk_data.get('documents'):
                    full_context += prev_chunk_data['documents'][0]
                    full_context += "\n\n--- [ (이전 문맥) ] ---\n\n"

                # --- 메인 청크 (정답) ---
                full_context += best_doc.page_content
                
                # --- 뒤 청크 조회 ---
                next_chunk_data = self._vectorstore.get(
                    where={"$and": [
                        {"source": source_file},
                        {"chunk_id": next_chunk_id_int}
                    ]},
                    include=["documents"]
                )
                if next_chunk_data and next_chunk_data.get('documents'):
                    full_context += "\n\n--- [ (다음 문맥) ] ---\n\n"
                    full_context += next_chunk_data['documents'][0]
                
                logger.info(f"[RAG Tool] Search complete. Returning expanded context (Source: {source_file}, Chunk: {best_chunk_id_int}).")
                return f"--- [Reference: RAG Search Result (Source: {source_file}, Page: {best_meta.get('page_number')}, Score: {best_score:.4f})] ---\n\n{full_context}\n\n--- [End of Search Result] ---"

            else:
                # 'chunk_id'가 없는 레거시 DB인 경우, 상위 K개만 반환
                logger.warning("[RAG Tool] 'chunk_id' not found in metadata. Returning top K results without expansion.")
                context = "--- [Reference: RAG Search Results (Non-Expanded)] ---\n\n"
                for i, (doc, score) in enumerate(docs_with_scores):
                    source = os.path.basename(doc.metadata.get('source', 'N/A'))
                    context += f"Fragment {i+1} (Source: {source}, Score: {score:.4f}):\n"
                    context += doc.page_content[:300] + "...\n" # 미리보기만 제공
                    context += "\n"
                context += "--- [End of Search Results] ---"
                return context
                
        except Exception as e:
            logger.error(f"[RAG Tool] Error during search invocation for query '{query}': {e}", exc_info=True)
            return f"Error: An exception occurred during the RAG search. Details: {e}"