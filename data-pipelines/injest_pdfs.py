import os
import logging
import chromadb
import boto3
from io import BytesIO
from typing import List

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata

from unstructured.partition.pdf import partition_pdf

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('unstructured').setLevel(logging.WARNING)
logging.getLogger('unstructured_inference').setLevel(logging.WARNING)
logging.getLogger('timm').setLevel(logging.WARNING)
logging.getLogger('pikepdf').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

# 1. MinIO (S3 호환) 서버 설정
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "academic-bucket")
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "ajou")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "software")

# 2. ChromaDB 서버 설정
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "academic_regulations")

# 3. RAG 파이프라인 설정
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200)) 
DEVICE_TYPE = os.getenv("DEVICE_TYPE", "cpu")

def load_embedding_model(model_name: str, device: str) -> HuggingFaceEmbeddings:
    """
    지정된 HuggingFace 임베딩 모델을 메모리에 로드합니다.
    """
    logging.info(f"Loading embedding model: {model_name} (Device: {device})")
    model_kwargs = {'device': device}
    encode_kwargs = {'normalize_embeddings': True}
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
        logging.info("Embedding model loaded successfully.")
        return embeddings
    except Exception as e:
        logging.error(f"Failed to load embedding model '{model_name}': {e}", exc_info=True)
        raise

def load_and_partition_documents_from_minio(
    bucket: str, endpoint: str, key: str, secret: str
) -> List:
    """
    MinIO (S3) 버킷에 연결하여 모든 PDF 파일을 찾아
    'unstructured'로 메모리 내에서 직접 파티셔닝합니다.
    (S3DirectoryLoader 대신 unstructured 로직 직접 구현)
    """
    logging.info(f"Connecting to MinIO bucket: {bucket} at {endpoint}")
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        use_ssl=False
    )
    
    pdf_files = []
    try:
        response = s3_client.list_objects_v2(Bucket=bucket)
        if 'Contents' not in response:
            logging.warning(f"No files found in bucket '{bucket}'.")
            return []
        
        for obj in response['Contents']:
            if obj['Key'].lower().endswith('.pdf'):
                pdf_files.append(obj['Key'])
    except Exception as e:
        logging.error(f"Failed to list objects in MinIO bucket: {e}", exc_info=True)
        raise
        
    if not pdf_files:
        logging.warning(f"No PDF files found in bucket '{bucket}'.")
        return []

    logging.info(f"Found {len(pdf_files)} PDF files. Starting partitioning...")
    
    all_elements = []
    for pdf_key in pdf_files:
        logging.info(f"  - Processing: {pdf_key}")
        try:
            pdf_obj = s3_client.get_object(Bucket=bucket, Key=pdf_key)
            pdf_bytes = pdf_obj['Body'].read()
            
            elements = partition_pdf(
                file=BytesIO(pdf_bytes),
                infer_table_structure=True, 
                strategy="hi_res", 
                languages=["kor"],
                metadata_filename=pdf_key 
            )
            all_elements.extend(elements)
        except Exception as e:
            logging.warning(f"Failed to partition PDF '{pdf_key}': {e}", exc_info=True)
    
    logging.info(f"Partitioning complete. {len(all_elements)} elements extracted.")
    return all_elements

def main_ingestion_pipeline() -> None:
    """
    전체 데이터 인제스천(Ingestion) 파이프라인을 실행합니다.
    1. MinIO에서 PDF 로드 및 Unstructured 파티셔닝
    2. [수정됨] 파일명(filename)별로 먼저 그룹화, 그 다음 페이지별로 그룹화
    3. Recursive 청킹 (Overlap 적용)
    4. 임베딩 모델 로드
    5. 메타데이터 필터링
    6. 원격 ChromaDB 서버에 접속하여 벡터 저장
    """
    try:
        # --- 1. Load & Partition ---
        all_elements = load_and_partition_documents_from_minio(
            bucket=MINIO_BUCKET,
            endpoint=MINIO_ENDPOINT_URL,
            key=MINIO_ACCESS_KEY,
            secret=MINIO_SECRET_KEY
        )
        if not all_elements:
            logging.info("No elements extracted from MinIO PDFs. Exiting pipeline.")
            return

        # --- 2. '파일명'별로 먼저 그룹화, 그 다음 '페이지 번호'별로 그룹화 ---
        logging.info("Grouping elements by filename, then by page number...")
        
        file_page_elements = {}
        for el in all_elements:
            page_num = el.metadata.page_number
            filename = el.metadata.filename
            
            if not page_num or not filename:
                continue

            if filename not in file_page_elements:
                file_page_elements[filename] = {}
            
            if page_num not in file_page_elements[filename]:
                file_page_elements[filename][page_num] = []
            
            file_page_elements[filename][page_num].append(str(el))
        
        logging.info(f"Creating page-level Documents across {len(file_page_elements)} files...")
        
        page_docs = []
        for filename, pages in file_page_elements.items():
            for page_num in sorted(pages.keys()):
                page_text = "\n\n".join(pages[page_num])
                
                clean_metadata = {
                    "source": filename,
                    "page_number": page_num
                }
                
                page_docs.append(Document(page_content=page_text, metadata=clean_metadata))

        logging.info(f"{len(page_docs)} page Documents created.")

        # --- 3. Split (Chunk) ---
        logging.info(f"Splitting {len(page_docs)} pages into chunks (Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP})...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        splits = text_splitter.split_documents(page_docs)
        logging.info(f"Split completed: {len(splits)} text chunks created.")

        # 문맥 확장을 위해 청크에 순서 ID와 안정적인 Chroma ID를 부여.
        logging.info("Adding sequential 'chunk_id' metadata and generating stable IDs...")
        
        chunk_ids = []
        for i, doc in enumerate(splits):
            doc.metadata["chunk_id"] = i 
            source_file = doc.metadata.get("source", "unknown_file")
            chunk_ids.append(f"{source_file}_chunk_{i}")

        # --- 4. Embed ---
        embeddings = load_embedding_model(EMBEDDING_MODEL, DEVICE_TYPE)

        # --- 5. Filter Metadata ---
        logging.info("Filtering complex metadata for ChromaDB compatibility...")
        filtered_splits = filter_complex_metadata(splits)

        # --- 6. Store to Remote ChromaDB ---
        logging.info(f"Connecting to ChromaDB server at {CHROMA_HOST}:{CHROMA_PORT}")
        client = chromadb.HttpClient(
            host=CHROMA_HOST, 
            port=CHROMA_PORT
        )
        
        # DB를 새로 구축할 때마다 기존 컬렉션을 삭제하여 중복 방지
        try:
            logging.warning(f"Attempting to delete existing collection: '{CHROMA_COLLECTION_NAME}' for a fresh start.")
            client.delete_collection(name=CHROMA_COLLECTION_NAME)
            logging.info(f"Successfully deleted old collection.")
        except Exception:
            logging.info(f"Collection '{CHROMA_COLLECTION_NAME}' not found, creating new one.")

        logging.info(f"Ingesting {len(filtered_splits)} chunks into new collection: '{CHROMA_COLLECTION_NAME}'")
        
        Chroma.from_documents(
            documents=filtered_splits,
            embedding=embeddings,
            client=client,
            collection_name=CHROMA_COLLECTION_NAME,
            ids=chunk_ids
        )

        logging.info("Data ingestion pipeline completed successfully!")

    except Exception as e:
        logging.error(f"An error occurred during the ingestion pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    main_ingestion_pipeline()