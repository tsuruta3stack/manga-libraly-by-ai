"""
ベクトルデータベース (ChromaDB) に関する設定とクライアントのインスタンスを定義します。
"""
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

def get_embedding(model_type="ollama"):
    if model_type == "openai":
        return OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
    else:
        return OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL, 
            model=settings.OLLAMA_EMBEDDING_MODEL
        )
# 埋め込みモデルのインスタンスを生成
embedding = get_embedding(settings.LLM_TYPE)

# 漫画の「あらすじ」を格納するChromaDBのコレクション
vectorDB = Chroma(
    collection_name="manga_vector",
    persist_directory=settings.CHROMA_URL,  # データの永続化先ディレクトリ
    embedding_function=embedding,
    collection_metadata={"hnsw:space": "cosine"}  # 類似度計算にコサイン類似度を使用
)

def get_vectorDB() -> Chroma:
    """FastAPIのDI(依存性注入)で、あらすじ用Chromaクライアントを取得するための関数。"""
    return vectorDB