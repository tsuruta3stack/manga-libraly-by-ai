"""
FastAPIアプリケーションのエントリーポイントです。
アプリの初期化、ミドルウェアの設定、APIルーターの組み込みを行います。
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.models.manga import create_db_and_tables

from app.api.v1.api import api_router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションの起動時と終了時に実行される処理を定義します。
    起動時にデータベースとテーブルを作成します。
    """
    create_db_and_tables()
    yield

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(
    title="contents know",
    description="コンテンツ消費を支える独立した脳みそ",
    version="0.0.1",
    lifespan=lifespan
)

# CORS (Cross-Origin Resource Sharing) ミドルウェアを追加
# フロントエンド(Streamlit)とバックエンド(FastAPI)が異なるポートで動作するため、
# オリジン間のリソース共有を許可する必要があります。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中は "*" で全てのオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーターをアプリケーションに組み込み
# /api/v1 プレフィックスでv1のAPIエンドポイントをルーティングします。
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    """
    アプリケーションのヘルスチェック用エンドポイント。
    アプリケーションが正常に動作しているか、またOllamaの設定を確認できます。
    """
    return {
        "status": "ok",
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_embedding_model": settings.OLLAMA_EMBEDDING_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "openai_embedding_model": settings.OPENAI_EMBEDDING_MODEL
    }