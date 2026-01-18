"""
APIのバージョン1のメインルーターです。
各機能（エンドポイント）のルーターをまとめ、アプリケーションに登録します。
"""
from fastapi import APIRouter
from app.api.v1.endpoints import chat, manga

# APIRouterのインスタンスを作成
api_router = APIRouter()

# チャット関連のエンドポイントをルーティング
# /chat というプレフィックスを付け、"chat" タグでグループ化します。
api_router.include_router(
    chat.router, prefix="/chat", tags=["chat"]
)
# 漫画関連のエンドポイントをルーティング
# /manga というプレフィックスを付け、"manga" タグでグループ化します。
api_router.include_router(
    manga.router, prefix="/manga", tags=["manga"]
)
