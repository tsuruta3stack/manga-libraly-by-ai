"""
AIアシスタントとのチャットに関するAPIエンドポイントを定義します。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.chat import LLMService

router = APIRouter()

class ChatQuery(BaseModel):
    """チャットリクエストのデータモデル"""
    thread_id: str
    message: str

def get_llm_service() -> LLMService:
    """DI (Dependency Injection) を使用して、LLMServiceのインスタンスを生成します。"""
    return LLMService()

@router.post("/chat")
async def chat(request: ChatQuery, service: LLMService = Depends(get_llm_service)) -> dict:
    """
    ユーザーからのメッセージを受け取り、AIアシスタントからの応答を返します。
    """
    response = await service.chat(request.thread_id, request.message)
    return {"response": response}

@router.get("/chat/{thread_id}/manga-ids")
async def get_found_manga_ids(thread_id: str, service: LLMService = Depends(get_llm_service)) -> dict:
    """
    指定されたスレッドIDの会話内でAIが見つけた漫画のIDリストを取得します。
    """
    response = await service.get_found_manga_ids(thread_id)
    return {"response": response}

@router.get("/chat/{thread_id}/search-queries")
async def get_search_queries(thread_id: str, service: LLMService = Depends(get_llm_service)) -> dict:
    """
    指定されたスレッドIDの会話内でAIが生成した検索クエリのリストを取得します。
    """
    response = await service.get_search_queries(thread_id)
    return {"response": response}