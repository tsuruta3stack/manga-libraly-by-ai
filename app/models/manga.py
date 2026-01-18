"""
漫画情報に関するデータモデルと、関連するデータベース操作を定義します。
SQLModelを使用して、データベースのテーブルとPydanticの検証モデルを同時に定義します。
"""
from sqlmodel import Field, SQLModel, Session, create_engine, Enum
from pydantic import BaseModel, Field as PyField
from datetime import datetime
from typing import Optional, List, Literal
from app.core.config import settings

# --- 基本となる漫画データモデル ---
"""
今回はjikan_apiを利用して漫画データを取得します。
https://docs.api.jikan.moe/#/manga/getmangabyid をベースにデータ項目を定義します。
"""

class MangaBase(SQLModel):
    """漫画の基本となるフィールドを定義したモデル。"""
    title: Optional[str] = None                # タイトル
    author: Optional[str] = None               # 著者
    serialization: Optional[str] = None        # 連載
    volumes: Optional[int] = None              # 巻数
    status: Optional[str] = None               # ステータス, 「完結」など
    synopsis: Optional[str] = None             # あらすじ
    score: Optional[float] = None              # 評価
    my_review: Optional[str] = None            # ユーザーの感想
    my_score: Optional[int] = None             # ユーザーの評価
    my_status: Optional[str] = None            # ユーザー管理のステータス, 「読みたい」「読んでいる」「読み終えた」
    image_url: Optional[str] = None            # 表紙画像のURL
    site_url: Optional[str] = None             # 参照元のURL
    site_id: Optional[int] = None              # 参照元でのID
    ai_tags: Optional[str] = None              # AIによる"SF, ギャグ, 熱い展開" のようなカンマ区切りの文字列
    ai_comment: Optional[str] = None           # AIによるコメント
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# --- APIのレスポンス・リクエスト用モデル ---

class MangaRead(MangaBase):
    """漫画情報を読み取る際のAPIレスポンスモデル。IDが含まれます。"""
    id: int

class MangaCreate(MangaBase):
    """新しい漫画を作成する際のAPIリクエストモデル。"""
    pass

class MangaUpdate(MangaBase):
    """漫画情報を更新する際のAPIリクエストモデル。全てのフィールドが任意です。"""
    pass

# --- データベースのテーブル定義 ---

class Manga(MangaBase, table=True):
    """データベースの`manga`テーブルに対応するモデル。"""
    id: Optional[int] = Field(default=None, primary_key=True)

# --- LLM連携用のデータモデル ---

class MangaForLLM(SQLModel):
    """LLMにコンテキストとして渡すための、情報を絞った漫画モデル。"""
    id: int = Field(description="データ管理用ID")
    title: Optional[str] = Field(default=None, description="漫画のタイトル")
    author: Optional[str] = Field(default=None, description="漫画の著者")
    serialization: Optional[str] = Field(default=None, description="漫画の連載誌")
    status: Optional[str] = Field(default=None, description="漫画のステータス, 「完結」など")
    synopsis: Optional[str] = Field(default=None, description="漫画のあらすじ")
    score: Optional[float] = Field(default=None, description="漫画の評価")
    my_review: Optional[str] = Field(default=None, description="ユーザーの感想")
    my_score: Optional[int] = Field(default=None, description="ユーザーの評価")
    my_status: Optional[Literal["読みたい", "読んでいる", "読み終えた"]] = Field(default=None, description="ユーザー管理のステータス, 「読みたい」「読んでいる」「読み終えた」")
    ai_tags: Optional[str] = Field(default=None, description="AIによるタグ")
    ai_comment: Optional[str] = Field(default=None, description="AIによるおすすめポイント")

def to_llm_data(manga_list: List[Manga]) -> List[dict]:
    """Mangaオブジェクトのリストを、LLM向けの辞書のリストに変換します。"""
    return [MangaForLLM.model_validate(m).model_dump() for m in manga_list]

def get_llm_description(model_class=MangaForLLM) -> str:
    """Mangaオブジェクトのリストを、LLM向けの説明文に変換します。"""
    description = []
    for name, field in model_class.model_fields.items():
        d = field.description or "説明なし"
        description.append(f"- {name}: {d}")
    return "\n".join(description)

# --- 検索API用のパラメータモデル ---

class MangaSearchKeywordParams(BaseModel):
    """キーワード検索APIのクエリパラメータモデル。"""
    keyword: str = PyField(default="", description="検索キーワード")  
    limit: int = PyField(default=10, description="最大件数")  

class MangaSearchQueryParams(BaseModel):
    """複合条件検索APIのクエリパラメータモデル。"""
    id: Optional[int] = Field(default=None, description="データ管理用ID")
    title: Optional[str] = Field(default=None, description="漫画のタイトル")
    author: Optional[str] = Field(default=None, description="漫画の著者")
    serialization: Optional[str] = Field(default=None, description="漫画の連載誌")
    status: Optional[Literal["Finished", "Publishing", "On Hiatus","Discontinued","Not yet published"]] = Field(default=None, description="漫画のステータス, 「Finished」, 「Publishing」, 「On Hiatus」, 「Discontinued」, 「Not yet published」")
    synopsis: Optional[str] = Field(default=None, description="漫画のあらすじ")
    score: Optional[float] = Field(default=None, description="漫画の評価", ge=0, le=10)
    score_filter_method: Literal["min", "max", "equal"] = Field(default="equal", description="漫画の評価のフィルター方法, 「min」「max」「equal」")
    my_review: Optional[str] = Field(default=None, description="ユーザーの感想")
    my_score: Optional[int] = Field(default=None, description="ユーザーの評価", ge=0, le=5)
    my_score_filter_method: Literal["min", "max", "equal"] = Field(default="equal", description="漫画のユーザー評価のフィルター方法, 「min」「max」「equal」")
    my_status: Optional[Literal["読みたい", "読んでいる", "読み終えた"]] = Field(default=None, description="ユーザー管理のステータス, 「読みたい」「読んでいる」「読み終えた」")
    ai_tags: Optional[str] = Field(default=None, description="AIによるタグ")
    limit: int = PyField(default=10, description="最大件数")

class MangaSearchVectorParams(BaseModel):
    """ベクトル検索APIのクエリパラメータモデル。"""
    keyword: str
    limit: int = PyField(default=10)

# --- データベースエンジンとセッションのセットアップ ---

sqlite_url = settings.SQLITE_URL
engine = create_engine(sqlite_url)

def create_db_and_tables():
    """データベースとテーブルを（存在しない場合）作成します。"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPIのDI(依存性注入)で使用するためのDBセッション生成関数。"""
    with Session(engine) as session:
        yield session
