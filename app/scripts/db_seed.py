import requests
import time
import json
from pydantic import BaseModel
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from app.models.manga import MangaCreate, Manga, engine, create_db_and_tables
from app.services.manga import MangaService
from sqlmodel import Session, select
from app.graph.nodes import llm
from app.models.chroma import vectorDB


"""
漫画情報に関するデータモデルと、関連するデータベース操作を定義します。
SQLModelを使用して、データベースのテーブルとPydanticの検証モデルを同時に定義します。
"""

# 1. Jikan APIからTOP漫画の基本情報を取得する
def fetch_top_manga(limit_count=300):
    """APIから生のデータを取得してリストで返す（通信担当）"""
    base_url = "https://api.jikan.moe/v4/top/manga"
    manga_list = []
    page = 1
    print(f"jilan apiからデータ取得開始（全{limit_count}件）")
    while len(manga_list) < limit_count:
        print(f"---{page}ページ目を取得中---")
        response = requests.get(f"{base_url}?page={page}")
        
        if response.status_code == 200:
            data = response.json().get('data', [])
            if not data: break
            manga_list.extend(data)
            page += 1
            time.sleep(2) # Rate Limit回避
        else:
            print(f"エラー: {response.status_code}")
            break
            
    return manga_list[:limit_count]

# 2 IDを使ってreviewを取得する
def fetch_manga_reviews(manga_list):
    manga_list_with_reviews = []
    base_url = "https://api.jikan.moe/v4/manga/"
    for i, manga in enumerate(manga_list):
        print(f"---{i+1}/{len(manga_list)}件目のレビューを取得中---")
        response = requests.get(f"{base_url}{manga['mal_id']}/reviews?preliminary=true")
        data = response.json().get('data', [])
        review_list = [item.get('review') for item in data]

        total_count = 0
        total_limit = 30000
        review_count = 0
        for review in review_list:
            total_count += len(review)
            review_count += 1
            if total_count > total_limit:
                break

        reviews = "\n\n---\n\n".join(review_list[:review_count])
        # print(review)
        manga.update({"reviews": reviews})
        manga_list_with_reviews.append(manga)
        time.sleep(2) # Rate Limit回避
    return manga_list_with_reviews

# 3 llmに翻訳＆コメントさせる
class AICommentOutput(BaseModel):
    synopsis_ja: str
    ai_tags: str
    ai_comment: str

def comment_by_llm(title:str, synopsis:str, genres:str, themes:str, reviews:str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
         [Role]
         あなたは漫画の情報を適切に解釈し翻訳・推薦するエキスパートです。
         [Task]
         1. 英語のsynopsis(あらすじ)を日本語に翻訳してください。
         2. synopsis(あらすじ)・genres(ジャンル)・themes(テーマ)・reviews(複数人の感想)を参考に、
            以下の項目を日本語で考えてください。
            - ai_tags: その漫画を表すジャンルなどを内包する7〜15個の日本語のタグ。カンマ区切り。
            - ai_comment: その漫画のおすすめポイントを400文字程度で簡潔にまとめる。
         [Output]
            - synopsis_ja: 翻訳したあらすじ
            - ai_tags: 7〜10個の日本語のタグ。カンマ区切り。
            - ai_comment: その漫画のおすすめポイント。
         """
         ),
         ("human", """
         [漫画の情報]
            - title: {title}
            - synopsis: {synopsis}
            - genres: {genres}
            - themes: {themes}
            - reviews: {reviews}
          """
        )
    ])
    chain = prompt | llm.with_structured_output(AICommentOutput)
    response = chain.invoke({"title": title,"synopsis": synopsis, "genres": genres, "themes": themes ,"reviews": reviews})
    print(response)
    try:
        return response.model_dump()
    except Exception as e:
        print(f"パースエラー: {e}")
        return {"synopsis_ja": synopsis, "ai_tags": "", "ai_comment": ""} # 失敗時は英語をそのまま返す

# 4. RDB保存：取得したデータを整形してSQLiteに書き込む
def save_manga_to_sqlite(raw_data_list, manga_service):
    """
    APIから取得済みのリストを受け取り、
    翻訳・整形してRDBに保存する（DB操作担当）
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
    """
    print(f"RDB保存開始 (全{len(raw_data_list)}件)")
    
    for i, item in enumerate(raw_data_list):
        print(f"---{i+1}/{len(raw_data_list)}件目を保存中---")
        
        # 既存確認
        existing = manga_service.session.exec(
                    select(Manga).where(Manga.site_id == item.get("mal_id"))
                ).first()
        if existing:
            print(f"Skip (Already exists): {item.get('title')}")
            continue

        try:
            # 翻訳＆追加項目（LLM呼び出し）
            result = comment_by_llm(
                title = item.get("title_japanese") or item.get("title"), 
                synopsis = item.get("synopsis"),
                genres = ",".join([g.get("name") for g in item.get("genres", [])]), 
                themes = ",".join([t.get("name") for t in item.get("themes", [])]), 
                reviews = item.get("reviews")
            )
            # データ整形
            manga_data = {
                "title": item.get("title_japanese") or item.get("title"),
                "author": ",".join([str(a.get("name")).replace(",", "") for a in item.get("authors", [])]),
                "serialization": ",".join([s.get("name") for s in item.get("serializations", [])]),
                "volumes": item.get("volumes"),
                "status": item.get("status"),
                "synopsis": result.get("synopsis_ja"),
                "score": item.get("score"),
                "image_url": item.get("images", {}).get("jpg", {}).get("large_image_url"),
                "site_url": item.get("url"),
                "site_id": item.get("mal_id"),
                "ai_tags": result.get("ai_tags"),
                "ai_comment": result.get("ai_comment")
            }
            
            # 保存実行
            manga_obj = MangaCreate.model_validate(manga_data)
            manga_service.create_manga(params=manga_obj, vector_sync=False)
            
            print(f"[{i+1}/{len(raw_data_list)}] Saved: {manga_data['title']}")
            time.sleep(1) # LLMサーバー(Ollama)の負荷調整用
            
        except Exception as e:
            print(f"Error saving {item.get('title')}: {e}")

# 3. ベクトルDB同期：一括でベクトル化する（共通処理）
def sync_vector_store_batch(vector_db, batch_size=30):
    """RDBの内容をベクトルDBへ一括登録する（ベクトル化担当）"""
    with Session(engine) as session:
        all_manga = session.exec(select(Manga)).all()
        print(f"ベクトル構築開始（全{len(all_manga)}件）---")
        docs = []
        ids = []
        for m in all_manga:
            content = f"タグ：{m.ai_tags},タイトル：{m.title},おすすめ：{m.ai_comment},あらすじ：{m.synopsis}"
            docs.append(Document(page_content=content, metadata={"id": m.id, "title": m.title}))
            ids.append(str(m.id))
        for i in range(0, len(docs), batch_size):
            vector_db.add_documents(docs[i:i+batch_size], ids=ids[i:i+batch_size])
            print(f" {i+len(docs[i:i+batch_size])}/{len(docs)}バッチ登録中")

# 4. 実行関数
def run_full_seed_pipeline(limit: int):
    # 1. テーブル作成
    create_db_and_tables()
    
    # 2. API取得 (既存関数)
    raw_data = fetch_top_manga(limit)
    raw_data_with_reviews = fetch_manga_reviews(raw_data)
    
    # 3. SQLite保存 (既存関数を少し修正：ID重複チェックを入れる)
    with Session(engine) as session:
        manga_service = MangaService(session, vectorDB)
        save_manga_to_sqlite(raw_data_with_reviews, manga_service)
        
    # 4. ベクトル同期 (既存関数)
    sync_vector_store_batch(vectorDB)