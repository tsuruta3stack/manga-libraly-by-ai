"""
漫画情報に関するAPIエンドポイントを定義します。
CRUD (作成、読み取り、更新、削除) 操作や、様々な検索機能を提供します。
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from app.models.manga import MangaRead, Manga, MangaCreate, MangaUpdate, MangaSearchKeywordParams, MangaSearchQueryParams,MangaSearchVectorParams, get_session
from app.models.chroma import get_vectorDB
from app.services.manga import MangaService
from sqlmodel import Session
from typing import List
from langchain_chroma import Chroma
from langchain_core.documents import Document
from sqlmodel import select
from app.scripts.db_seed import run_full_seed_pipeline

router = APIRouter()

def get_manga_service(
        session: Session = Depends(get_session), 
        vectorDB: Chroma = Depends(get_vectorDB)
    ) -> MangaService:
    """
    DI (Dependency Injection) を使用して、MangaServiceのインスタンスを生成します。
    SQLModelのセッションとChromaDBのクライアントをサービスに渡します。
    """
    return MangaService(session, vectorDB)

@router.get("/manga/batch", response_model=List[MangaRead])
def batch_get_manga(
    ids: str = Query(..., description="カンマ区切りの漫画IDリスト"), 
    service: MangaService = Depends(get_manga_service)
) -> List[MangaRead]:
    """複数の漫画IDに基づいて、漫画情報のリストを一括で取得します。"""
    manga_ids_int = [int(id.strip()) for id in ids.split(",") if id.strip()]
    manga_list = service.get_manga_list_by_ids(manga_ids_int)
    return manga_list

@router.get("/manga/{manga_id}", response_model=MangaRead)
def get_manga(manga_id: int, service: MangaService = Depends(get_manga_service)) -> MangaRead:
    """指定されたIDの漫画情報を取得します。"""
    manga = service.get_manga(manga_id)
    return manga

@router.post("/manga", response_model=MangaRead)
def create_manga(params: MangaCreate, service: MangaService = Depends(get_manga_service)) -> MangaRead:
    """新しい漫画情報を作成します。"""
    manga = service.create_manga(params)
    return manga

@router.patch("/manga/{manga_id}", response_model=MangaRead)
def update_manga(manga_id: int, params: MangaUpdate, service: MangaService = Depends(get_manga_service)) -> MangaRead:
    """既存の漫画情報を更新します。"""
    manga = service.update_manga(manga_id, params)
    return manga

@router.delete("/manga/{manga_id}", response_model=MangaRead)
def delete_manga(manga_id: int, service: MangaService = Depends(get_manga_service)) -> MangaRead:
    """指定されたIDの漫画情報を削除します。"""
    manga = service.delete_manga(manga_id)
    return manga

@router.get("/search_manga_by_keyword", response_model=List[MangaRead])
def get_manga_list_by_keyword(params: MangaSearchKeywordParams = Depends(), service: MangaService = Depends(get_manga_service)) -> List[MangaRead]:
    """キーワードに基づいて漫画を検索します。"""
    manga_list = service.get_manga_list_by_keyword(params)
    return manga_list

@router.get("/search_manga_by_query", response_model=List[MangaRead])
def get_manga_list_by_query(params: MangaSearchQueryParams = Depends(),service: MangaService = Depends(get_manga_service)) -> List[MangaRead]:
    """より複雑なクエリ条件に基づいて漫画を検索します。"""
    manga_list = service.get_manga_list_by_query(params)
    return manga_list

@router.get("/search_manga_by_vector", response_model=List[MangaRead])
def get_manga_list_by_vector(params: MangaSearchVectorParams = Depends(),service: MangaService = Depends(get_manga_service)) -> List[MangaRead]:
    """ベクトル検索（セマンティック検索）を使用して、クエリの意味に近い漫画を検索します。"""
    manga_list = service.get_manga_list_by_vector(params)
    return manga_list

@router.get("/get_manga_count", response_model=int)
def get_manga_count(service: MangaService = Depends(get_manga_service)):
    return service.get_manga_count()

@router.post("/seed")
async def seed_database(background_tasks: BackgroundTasks, limit: int = 300):
    """
    Jikan APIからデータを取得し、LLM加工・DB格納をバックグラウンドで開始します。
    """
    # 非同期でパイプラインを実行
    background_tasks.add_task(run_full_seed_pipeline, limit)
    
    return {"message": f"Started seeding process for {limit} mangas in background."}
