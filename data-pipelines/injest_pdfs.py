import os
import logging
import chromadb
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import S3DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 환경 변수에서 설정값 로드 ---

# MinIO (S3 호환) 서버 설정
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "academic-data")
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

# ChromaDB 서버 설정
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "academic_regulations")

# RAG 파이프라인 설정
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))
DEVICE_TYPE = os.getenv("DEVICE_TYPE", "cpu") # or "cuda" if GPU is available

def load_embedding_model(model_name: str, device: str) -> HuggingFaceEmbeddings:
    """
    지정된 HuggingFace 임베딩 모델을 메모리에 로드합니다.
    """
    logging.info(f"Loading embedding model: {model_name} (Device: {device})")
    model_kwargs = {'device': device}
    encode_kwargs = {'normalize_embeddings': True} # 벡터 검색 성능 향상을 위해 정규화
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
        logging.info("Embedding model loaded successfully.")
        return embeddings
    except Exception as e:
        logging.error(f"Failed to load embedding model '{model_name}': {e}")
        raise

def load_documents_from_minio(bucket: str, endpoint: str, key: str, secret: str) -> List[Document]:
    """
    MinIO (S3) 버킷에서 PDF 문서들을 로드합니다.
    """
    logging.info(f"Loading documents from MinIO bucket: {bucket} at {endpoint}")
    try:
        loader = S3DirectoryLoader(
            bucket=bucket,
            endpoint_url=endpoint,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            use_ssl=False 
        )
        docs = loader.load()
        
        if not docs:
            logging.warning(f"No documents found in bucket '{bucket}'.")
            return []
            
        logging.info(f"Successfully loaded {len(docs)} document pages from MinIO.")
        return docs
    except Exception as e:
        # (예: Boto3/Botocore 라이브러리 누락, 인증 실패 등)
        logging.error(f"Error loading documents from MinIO: {e}")
        logging.error("Please ensure 'boto3' and 'botocore' are installed.")
        raise

def split_documents(docs: List[Document], chunk_size: int, chunk_overlap: int) -> List[Document]:
    """
    로드된 문서를 LLM 컨텍스트에 맞게 작은 청크로 분할합니다.
    """
    logging.info(f"Splitting {len(docs)} pages into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    splits = text_splitter.split_documents(docs)
    logging.info(f"Split completed: {len(splits)} text chunks created.")
    return splits

def main_ingestion_pipeline() -> None:
    """
    전체 데이터 인제스천(Ingestion) 파이프라인을 실행합니다.
    1. MinIO에서 PDF 로드
    2. 텍스트 청크로 분할
    3. 임베딩 모델 로드
    4. 원격 ChromaDB 서버에 접속하여 벡터 저장
    """
    try:
        # --- 1. Load ---
        documents = load_documents_from_minio(
            bucket=MINIO_BUCKET,
            endpoint=MINIO_ENDPOINT_URL,
            key=MINIO_ACCESS_KEY,
            secret=MINIO_SECRET_KEY
        )
        if not documents:
            logging.info("No documents to process. Exiting pipeline.")
            return

        # --- 2. Split ---
        splits = split_documents(documents, CHUNK_SIZE, CHUNK_OVERLAP)

        # --- 3. Embed ---
        embeddings = load_embedding_model(EMBEDDING_MODEL, DEVICE_TYPE)

        # --- 4. Store ---
        logging.info(f"Connecting to ChromaDB server at {CHROMA_HOST}:{CHROMA_PORT}")
        
        client = chromadb.HttpClient(
            host=CHROMA_HOST, 
            port=CHROMA_PORT
        )
        
        logging.info(f"Ingesting {len(splits)} chunks into collection: '{CHROMA_COLLECTION_NAME}'")

        Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            client=client,
            collection_name=CHROMA_COLLECTION_NAME
        )

        logging.info("Data ingestion pipeline completed successfully!")

    except Exception as e:
        logging.error(f"An error occurred during the ingestion pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    main_ingestion_pipeline()