from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config import settings

def get_vectorstore(collection_suffix: str = "main") -> QdrantVectorStore:
    if not settings.openai_api_key or settings.openai_api_key == "your_key_here":
        print("WARNING: OPENAI_API_KEY is not set. Falling back to FakeEmbeddings for dry-run/mock mode.")
        from langchain_core.embeddings import FakeEmbeddings
        embeddings = FakeEmbeddings(size=1536)
    else:
        embeddings = OpenAIEmbeddings(
            model=settings.openai_embed_model,
            api_key=settings.openai_api_key
        )


    collection_name = f"{settings.qdrant_collection}_{collection_suffix}"
    
    try:
        # Attempt to connect to remote Qdrant server
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
            timeout=3.0
        )
        # Verify connection by calling get_collections
        client.get_collections()
    except Exception:
        local_path = f"./qdrant_local/{collection_suffix}"
        print(f"INFO: Qdrant server at {settings.qdrant_url} is not running or unreachable. Falling back to local disk storage at '{local_path}'...")
        client = QdrantClient(path=local_path)


    # Ensure collection exists
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
