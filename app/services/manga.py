"""
漫画情報に関するビジネスロジックを処理するサービスクラス。
データベースセッションとベクトルDBクライアントを操作します。
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select, col, or_, desc
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.models.manga import Manga, MangaCreate, MangaUpdate, MangaSearchKeywordParams, MangaSearchQueryParams, MangaSearchVectorParams

class MangaService:
    """漫画サービスのクラス"""
    def __init__(self, session: Session,
                 vectorDB: Optional[Chroma] = None):
        """
        コンストラクタ

        Args:
            session (Session): SQLModelのデータベースセッション
            vectorDB (Optional[Chroma]): ベクトルDBクライアント
        """
        self.session = session
        self.vectorDB = vectorDB

    def get_manga(self, manga_id: int) -> Optional[Manga]:
        """IDで単一の漫画を取得します。"""
        return self.session.get(Manga, manga_id)
    
    def get_manga_list_by_ids(self, manga_ids: list[int]) -> list[Manga]:
        """複数のIDに基づいて漫画のリストを取得します。"""
        statement = select(Manga).where(Manga.id.in_(manga_ids))
        return self.session.exec(statement).all()

    def create_manga(self, params: MangaCreate, vector_sync: bool = True) -> Manga:
        """新しい漫画を作成します。"""
        manga = Manga.model_validate(params)
        manga.created_at = datetime.now()
        manga.updated_at = datetime.now()
        self.session.add(manga)
        self.session.commit()
        self.session.refresh(manga)
        # ベクトル同期が有効な場合、ベクトルを作成
        # if (manga.summary or manga.tags) and vector_sync:
        #     self._sync_vector(manga)
        return manga

    def update_manga(self, manga_id: int, params: MangaUpdate, vector_sync: bool = True) -> Optional[Manga]:
        """既存の漫画を更新します。"""
        manga = self.session.get(Manga, manga_id)
        if not manga:
            return None
        update_data = params.model_dump(exclude_unset=True)
        manga.sqlmodel_update(update_data)
        manga.updated_at = datetime.now()
        self.session.add(manga)
        self.session.commit()
        self.session.refresh(manga)
        # # ベクトル同期が有効で、対象フィールドが更新された場合、ベクトルを更新
        # if ("summary" in update_data or "tags" in update_data) and vector_sync:
        #     self._sync_vector(manga)
        return manga

    def delete_manga(self, manga_id: int) -> Optional[Manga]:
        """漫画を削除します。"""
        manga = self.session.get(Manga, manga_id)
        if not manga:
            return None
        self.session.delete(manga)
        self.session.commit()
        # 削除したオブジェクトを返すことで、エンドポイント側で情報を利用できる
        return manga
    
    def get_manga_list_by_keyword(self, params: MangaSearchKeywordParams) -> List[Manga]:
        """キーワードで漫画を検索します（タイトル、あらすじ、タグが対象）。"""
        statement = select(Manga).where(
            or_(
                col(Manga.title).like(f"%{params.keyword}%"),
                col(Manga.synopsis).like(f"%{params.keyword}%"),
                col(Manga.ai_tags).like(f"%{params.keyword}%")
            )
        )
        statement = statement.order_by(desc(Manga.score))
        statement = statement.limit(params.limit) 
        results = self.session.exec(statement).all()
        return list(results)
    
    def get_manga_list_by_query(self, params: MangaSearchQueryParams) -> List[Manga]:
        """複数の検索条件を組み合わせて漫画を検索します。
            id: int = Field(description="データ管理用ID")
            title: Optional[str] = Field(default=None, description="漫画のタイトル")
            author: Optional[str] = Field(default=None, description="漫画の著者")
            serialization: Optional[str] = Field(default=None, description="漫画の連載誌")
            status: Optional[str] = Field(default=None, description="漫画のステータス, 「完結」など")
            synopsis: Optional[str] = Field(default=None, description="漫画のあらすじ")
            score: Optional[float] = Field(default=None, description="漫画の評価", ge=0, le=10)
            score_filter_method: Literal["min", "max", "equal"] = Field(default="equal", description="漫画の評価のフィルター方法, 「min」「max」「equal」")
            my_review: Optional[str] = Field(default=None, description="ユーザーの感想")
            my_score: Optional[int] = Field(default=None, description="ユーザーの評価", ge=0, le=5)
            my_score_filter_method: Literal["min", "max", "equal"] = Field(default="equal", description="漫画のユーザー評価のフィルター方法, 「min」「max」「equal」")
            my_status: Optional[Literal["読みたい", "読んでいる", "読み終えた"]] = Field(default=None, description="ユーザー管理のステータス, 「読みたい」「読んでいる」「読み終えた」")
            ai_tags: Optional[str] = Field(default=None, description="AIによるタグ")
        """
        statement = select(Manga)
        if params.id:
            statement = statement.where(Manga.id == params.id)
        if params.title:
            statement = statement.where(col(Manga.title).like(f"%{params.title}%"))
        if params.author:
            statement = statement.where(col(Manga.author).like(f"%{params.author}%"))
        if params.serialization:
            statement = statement.where(col(Manga.serialization).like(f"%{params.serialization}%"))
        if params.status:
            statement = statement.where(Manga.status == params.status)
        if params.synopsis:
            statement = statement.where(col(Manga.synopsis).like(f"%{params.synopsis}%"))
        if params.score:
            if params.score_filter_method == "min":
                statement = statement.where(Manga.score >= params.score)
            elif params.score_filter_method == "max":
                statement = statement.where(Manga.score <= params.score)
            else:
                statement = statement.where(Manga.score == params.score)
        if params.my_review:
            statement = statement.where(col(Manga.my_review).like(f"%{params.my_review}%"))
        if params.my_score:
            if params.my_score_filter:
                statement = statement.where(Manga.my_score >= params.my_score)
            elif params.my_score_filter == "max":
                statement = statement.where(Manga.my_score <= params.my_score)
            else:
                statement = statement.where(Manga.my_score == params.my_score)
        if params.my_status:
            statement = statement.where(Manga.my_status == params.my_status)
        if params.ai_tags:
            statement = statement.where(col(Manga.ai_tags).like(f"%{params.ai_tags}%"))

        # statement = statement.order_by(desc(Manga.updated_at))
        statement = statement.order_by(desc(Manga.score))
        statement = statement.limit(params.limit) 
        results = self.session.exec(statement).all()
        return list(results)

    def get_manga_list_by_vector(self, params: MangaSearchVectorParams) -> List[Manga]:
        """ベクトル検索（セマンティック検索）を実行します。"""
        docs = self.vectorDB.similarity_search(params.keyword, k=params.limit)
        if not docs:
            return []
        # 取得したドキュメントから漫画IDを抽出
        manga_ids = [int(doc.metadata["id"]) for doc in docs]
        
        # 漫画IDでデータベースから漫画情報を取得
        statement = select(Manga).where(Manga.id.in_(manga_ids))
        results = self.session.exec(statement).all()
        
        # ベクトル検索の類似度順に並べ替える
        result_map = {m.id: m for m in results}
        ordered_results = [result_map[m_id] for m_id in manga_ids if m_id in result_map]
        
        return ordered_results
    
    def get_manga_count(self) -> int:
        """漫画の件数を取得します。"""
        statement = select(Manga)
        return len(self.session.exec(statement).all())
    
    def delete_all_manga_data(self):
        """漫画データを削除します"""
        if self.vectorDB:
            self.vectorDB.delete_collection()
        self.session.delete_all(Manga)
        self.session.commit()