import json
import logging
import os
import warnings
import boto3
from typing import Type, List, Any
from crewai.tools import BaseTool
from pydantic import BaseModel, PrivateAttr
from langchain_chroma import Chroma
import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from schemas.tool_input import SearchInternalDocsInput, AdaptiveRagInput
from schemas.task_output import RagPlan
from openai import OpenAI

logger = logging.getLogger(__name__)

class SearchOrgChartTool(BaseTool):
    name: str = "조직도 및 업무 분장표 로드 도구"
    description: str = "업무분장표 JSON 전체를 로드합니다."
    
    _minio_bucket: str = PrivateAttr()
    _minio_object_key: str = PrivateAttr()
    _s3_client = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._minio_bucket = os.getenv("MINIO_BUCKET", "academic-bucket")
        self._minio_object_key = os.getenv("ORG_CHART_JSON_KEY", "software_org_chart.json")
        try:
            self._s3_client = boto3.client(
                's3', endpoint_url=os.getenv("MINIO_ENDPOINT_URL", "http://minio:9000"),
                aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "ajou"),
                aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "software"), use_ssl=False
            )
        except:
            self._s3_client = None

    def _run(self) -> str:
        if self._s3_client is None: return "Error: MinIO client not initialized."
        try:
            response = self._s3_client.get_object(Bucket=self._minio_bucket, Key=self._minio_object_key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            return json.dumps(data.get("업무분장표", []), indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error loading org chart: {e}"

class ListKnowledgeBaseFilesTool(BaseTool):
    name: str = "RAG 파일 목록 조회"
    description: str = "DB에 저장된 PDF 파일명 목록을 반환합니다."
    
    _client = PrivateAttr(default=None)
    _collection_name: str = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            self._collection_name = os.getenv("CHROMA_COLLECTION_NAME", "academic_regulations")
            self._client = chromadb.HttpClient(
                host=os.getenv("CHROMA_HOST", "chromadb"), 
                port=int(os.getenv("CHROMA_PORT", 8000))
            )
        except:
            self._client = None

    def _run(self) -> List[str]:
        if not self._client: return []
        try:
            coll = self._client.get_collection(name=self._collection_name)
            metas = coll.get(include=["metadatas"])['metadatas']
            return sorted(list(set(m['source'] for m in metas if m and 'source' in m)))
        except:
            return []\

class SearchInternalDocsTool(BaseTool):
    name: str = "RAG 단일 검색 (문맥 확장 포함)"
    description: str = "특정 파일에서 쿼리와 유사한 내용을 검색하고, 전후 문맥을 포함하여 상세 내용을 반환합니다."
    args_schema: Type[BaseModel] = SearchInternalDocsInput
    
    _vectorstore: Chroma = PrivateAttr(default=None)
    _search_k: int = PrivateAttr(default=6) 
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._search_k = int(os.getenv("VECTOR_DB_K", 6))
        
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask"),
                model_kwargs={'device': os.getenv("DEVICE_TYPE", "cpu")}
            )
            client = chromadb.HttpClient(
                host=os.getenv("CHROMA_HOST", "chromadb"), 
                port=int(os.getenv("CHROMA_PORT", 8000))
            )
            self._vectorstore = Chroma(
                client=client,
                collection_name=os.getenv("CHROMA_COLLECTION_NAME", "academic_regulations"),
                embedding_function=embeddings
            )
        except Exception as e:
            logger.error(f"RAG Init Failed: {e}")

    def _run(self, query: str, source_file: str) -> str:
        if not self._vectorstore: return "Error: DB Not Initialized"
        
        logger.info(f"[RAG Tool] Search: '{query}' in '{source_file}' (K={self._search_k})")
        
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                docs_with_scores = self._vectorstore.similarity_search_with_relevance_scores(
                    query, k=self._search_k, filter={"source": source_file}
                )
            
            if not docs_with_scores:
                return f"Info: '{source_file}'에서 '{query}' 관련 내용을 찾지 못했습니다."
            
            final_result = ""
            # 상위 3개 결과에 대해서만 앞뒤 문맥 확장 수행
            top_docs = docs_with_scores[:3]
            
            for i, (doc, score) in enumerate(top_docs):
                meta = doc.metadata
                chunk_id = meta.get('chunk_id')
                context_block = ""
                
                if chunk_id is not None:
                    # (1) 이전 청크
                    prev_data = self._vectorstore.get(
                        where={"$and": [{"source": source_file}, {"chunk_id": chunk_id - 1}]},
                        include=["documents"]
                    )
                    if prev_data and prev_data.get('documents'):
                        context_block += f"[이전 문맥]\n{prev_data['documents'][0]}\n"

                    # (2) 현재 청크
                    context_block += f"[검색된 내용 (Score: {score:.4f})]\n{doc.page_content}\n"
                    
                    # (3) 다음 청크
                    next_data = self._vectorstore.get(
                        where={"$and": [{"source": source_file}, {"chunk_id": chunk_id + 1}]},
                        include=["documents"]
                    )
                    if next_data and next_data.get('documents'):
                        context_block += f"[다음 문맥]\n{next_data['documents'][0]}\n"
                        
                    # (4) 다다음 청크
                    next_data = self._vectorstore.get(
                        where={"$and": [{"source": source_file}, {"chunk_id": chunk_id + 2}]},
                        include=["documents"]
                    )
                    if next_data and next_data.get('documents'):
                        context_block += f"[다다음 문맥]\n{next_data['documents'][0]}\n"
                else:
                    context_block += f"[검색된 내용]\n{doc.page_content}\n"
                
                final_result += f"\n=== [Result #{i+1}] ===\n{context_block}\n"

            return final_result

        except Exception as e:
            logger.error(f"[RAG Tool] Error: {e}", exc_info=True)
            return f"Search Error: {e}"

class AdaptiveRagSearchTool(BaseTool):
    name: str = "지능형 규정집 통합 검색 도구"
    description: str = "사용자의 질문을 입력받아 최적의 PDF를 찾아 검색합니다."
    args_schema: Type[BaseModel] = AdaptiveRagInput
    
    _list_tool: ListKnowledgeBaseFilesTool = PrivateAttr()
    _search_tool: SearchInternalDocsTool = PrivateAttr()
    _openai_client: OpenAI = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._list_tool = ListKnowledgeBaseFilesTool()
        self._search_tool = SearchInternalDocsTool()
        self._openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _run(self, query: Any = None, **kwargs) -> str:
        # 입력 파라미터 방어 로직
        if not query:
            query = kwargs.get('description') or kwargs.get('input') or kwargs.get('user_query')
        if isinstance(query, dict):
            query = query.get('query') or query.get('description') or str(query)
        if not query and kwargs:
            for v in kwargs.values():
                if isinstance(v, str) and len(v) > 5:
                    query = v
                    break
        query = str(query) if query else "내용 없음"
            
        files = self._list_tool._run()
        if not files: return "Error: 검색 가능한 문서가 없습니다."
        files_str = "\n".join(files)

        # 프롬프트 전략: '검색어 생성 원칙'을 제시하여 어떤 주제가 와도 대응 가능하게 함
        prompt = f"""
        당신은 대학 행정 데이터 검색 전문가입니다.
        사용자의 질문을 해결하기 위해 가장 적합한 PDF 파일 1개를 선택하고,
        RAG 검색을 위한 '3가지 검색어'를 생성하세요.

        [검색어 생성 원칙]
        1. **직관적 검색어**: 질문의 핵심 키워드를 그대로 사용 (예: '졸업 요건', '장학금 기준').
        2. **구조적 검색어**: 규정집의 특성을 고려하여 '표', '별표', '세부 기준', '예외 사항', '유의사항' 등의 단어를 조합 (예: '졸업 세부 기준', '장학금 지급 제한 예외').
        3. **연관 검색어**: 질문의 문맥을 파악하여 행정적으로 연관된 공식 용어를 유추 (예: '심화 과정', '수혜 자격', '이수 구분').

        [사용 가능한 파일 목록]
        {files_str}
        """
        
        try:
            completion = self._openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query},
                ],
                response_format=RagPlan,
            )
            plan = completion.choices[0].message.parsed
            target_file = plan.target_filename
            queries = plan.search_queries
            
            logger.info(f"📂 [AdaptiveRAG] Target: {target_file}")
            logger.info(f"❓ [AdaptiveRAG] Queries: {queries}")
            
            if target_file not in files: target_file = files[0]

        except Exception as e:
            logger.error(f"Planning Failed: {e}")
            target_file = files[0] if files else ""
            queries = [query]

        aggregated_results = f"--- [검색 대상: {target_file}] ---\n"
        for q in queries:
            search_res = self._search_tool._run(query=q, source_file=target_file)
            aggregated_results += f"\n[Q: {q}]\n{search_res}\n"
            
        return aggregated_results