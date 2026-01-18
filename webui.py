"""
このスクリプトは、Streamlitを使用して「コンテンツ脳」アプリケーションのWebインターフェースを構築します。
漫画ライブラリの管理、作品の検索、そしてAIアシスタントによる推薦機能を提供します。
"""
import streamlit as st
import requests
import uuid

# --- ページ設定とAPI情報 ---
st.set_page_config(page_title="漫画ライブラリ", layout="wide")
# バックエンドAPIのエンドポイントURL
API_URL = "http://localhost:8000/api/v1"

# --- セッション状態の初期化 ---
# アプリケーション全体で利用する変数をセッション状態で管理します。
if "edit_target" not in st.session_state:
    st.session_state["edit_target"] = None  # 現在編集中の漫画
if "search_results" not in st.session_state:
    st.session_state["search_results"] = []  # 検索結果やAIによる推薦結果
if "messages" not in st.session_state:
    st.session_state.messages = []  # AIアシスタントとのチャット履歴
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())  #チャットのスレッドを一意に識別するID

# --- UIコンポーネント ---

def display_manga_cards(manga_list, col_n=4):
    """
    漫画のリストをカード形式のグリッドで表示します。

    Args:
        manga_list (list): 表示する漫画情報の辞書のリスト。
        col_n (int): グリッドの列数。
    """
    if not manga_list:
        st.info("表示できる漫画がありません。")
        return

    # 漫画リストを `col_n` 個ずつに区切り、列を作成して表示
    for i in range(0, len(manga_list), col_n):
        cols = st.columns(col_n)
        for j, manga in enumerate(manga_list[i : i + col_n]):
            with cols[j]:
                with st.container(border=True):
                    if manga.get("image_url"):
                        st.image(manga["image_url"])
                    st.markdown(f"**{manga['title']}**")
                    st.caption(f"{manga['author']} / ⭐ {manga.get('score', 0)}")
                    # 「編集」ボタンが押されたら、その漫画をセッション状態に保存して再実行
                    if st.button("編集", key=f"edit_{manga['id']}", width='stretch'):
                        st.session_state["edit_target"] = manga
                        st.rerun()

# ==========================================
# 1. サイドバー: AIアシスタント
# ==========================================
with st.sidebar:
    st.header("AIアシスタント")

    # チャット履歴の表示
    chat_container = st.container(height=600, border=False)
    with chat_container:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

    # ユーザーからのチャット入力
    if prompt := st.chat_input("おすすめの漫画は？"):
        # ユーザーのメッセージを表示・保存
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # バックエンドAPIにリクエストを送信し、AIからの応答を取得
        with st.chat_message("assistant"):
            with st.spinner("AIが考えています..."):
                res = requests.post(f"{API_URL}/chat/chat", 
                    json={
                        "thread_id": st.session_state.thread_id, 
                        "message": prompt
                    }
                )
                
                if res.status_code == 200:
                    # アシスタントの応答を表示・保存
                    answer = res.json()["response"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

                    # AIが漫画を推薦した場合、そのIDリストをバックエンドから取得
                    id_res = requests.get(f"{API_URL}/chat/chat/{st.session_state.thread_id}/manga-ids")
                    if id_res.status_code == 200:
                        found_ids = id_res.json()["response"]
                        if found_ids:
                            # 推薦された漫画の詳細情報を一括で取得
                            ids_query = ",".join(map(str, found_ids))
                            res_batch = requests.get(f"{API_URL}/manga/manga/batch", params={"ids": ids_query})
                            if res_batch.status_code == 200:
                                # 検索結果を推薦された漫画で更新
                                st.session_state["search_results"] = res_batch.json()
                                st.session_state["edit_target"] = None
                                st.toast(f"{len(found_ids)}件の漫画を見つけました！")
                    
                    st.rerun()

    # 会話をリセットするボタン
    if st.button("会話をリセット"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state["search_results"] = []
        st.rerun()
    st.text(f"スレッドID: {st.session_state.thread_id}")

# ==========================================
# 2. メイン画面
# ==========================================
st.title("漫画ライブラリ")
st.divider()
st.header("漫画検索")
# --- 手動検索フィルター ---
with st.expander("簡易検索"):
    c1, c2 = st.columns([4, 1])
    keyword = c1.text_input("キーワード", placeholder="タイトル・著者・タグ...")
    limit_keyword_search = c2.slider("最大件数（簡易）", 1, 50, 10)
    if c2.button("検索実行（簡易）", width='stretch'):
        # バックエンドに検索リクエストを送信
        res = requests.get(f"{API_URL}/manga/search_manga_by_keyword", params={"keyword": keyword, "limit": limit_keyword_search})
        if res.status_code == 200:
            st.session_state["search_results"] = res.json()
            st.session_state["edit_target"] = None
            st.rerun()

with st.expander("詳細検索"):
    c1, c2 = st.columns([4, 1])
    title = c1.text_input("タイトル", placeholder="タイトル(部分一致)") or None
    author = c1.text_input("著者", placeholder="著者(部分一致)") or None
    serialization = c1.text_input("連載誌", placeholder="連載誌(部分一致)") or None
    synopsis = c1.text_input("あらすじ", placeholder="あらすじ(部分一致)") or None
    status = c1.selectbox("ステータス", [None, "Finished", "Publishing", "On Hiatus","Discontinued","Not yet published"]) or None
    score = c1.number_input("スコア", min_value=0.0, max_value=10.0, value=None, step=0.1) or None
    score_filter_method = c1.selectbox("スコアフィルター", ["min", "max", "equal"]) or None
    my_review = c1.text_input("感想", placeholder="感想(部分一致)") or None
    my_score = c1.number_input("評価", min_value=0, max_value=5, value=None, step=1) or None
    my_score_filter_method = c1.selectbox("評価フィルター", ["min", "max", "equal"]) or None
    my_status = c1.selectbox("ユーザーステータス", [None, "読みたい", "読んでいる", "読み終えた"]) or None
    ai_tag = c1.text_input("タグ", placeholder="タグ(カンマ区切り, 部分一致)") or None
    
    limit_query_search = c2.slider("最大件数（詳細）", 1, 50, 10) or None
    if c2.button("検索実行（詳細）", width='stretch'):
        # バックエンドに検索リクエストを送信
        res = requests.get(f"{API_URL}/manga/search_manga_by_query", 
            params={
                "title": title,
                "author": author,
                "serialization": serialization,
                "synopsis": synopsis,
                "status": status,
                "score": score,
                "score_filter_method": score_filter_method,
                "my_review": my_review,
                "my_score": my_score,
                "my_score_filter_method": my_score_filter_method,
                "my_status": my_status,
                "ai_tag": ai_tag,
                "limit": limit_query_search
            }
        )
        if res.status_code == 200:
            st.session_state["search_results"] = res.json()
            st.session_state["edit_target"] = None
            st.rerun()

# 現在の検索結果に基づいて漫画カードを表示
display_manga_cards(st.session_state["search_results"])

# --- 漫画編集フォーム ---
# 編集対象の漫画が選択されている場合にフォームを表示
st.divider()
st.header("漫画編集")
if st.session_state["edit_target"]:
    target = st.session_state["edit_target"]
    with st.container(border=True):
        st.subheader(f"📝 編集: {target['title']}")
        with st.form("edit_form"):
            col_img, col_form = st.columns([1, 3])
            # 漫画情報の編集用フォームフィールド
            with col_img:
                if target.get("image_url"):
                    st.image(target["image_url"], width='stretch')
                st.markdown(
                    f"""
                    ###### My_anime_list: 
                    - 評価：⭐ {target.get('score', 0)}
                    - 巻数: {target.get("volumes", "")}
                    - 連載: {target.get("serialization", "")}
                    - ステータス: {target.get("status", "")}
                    - リンク: {target.get("site_url", "")}
                    """
                    )

            with col_form:
                basic_info = st.markdown(
                    f"""
                    ###### タイトル\n
                    {target.get("title", "")}\n
                    ###### 著者\n
                    {target.get("author", "")}\n
                    ###### あらすじ\n
                    {target.get("synopsis", "")}\n
                    """
                )
                new_tags = st.text_area("タグ", value=target.get("ai_tags", ""))
                new_review = st.text_area("感想", value=target.get("my_review", ""), height=100)
                new_score = st.slider("評価", 1, 5, target.get("my_score", 1))

            # フォームの送信ボタン
            col_btn1, col_btn2 = st.columns([1, 5])
            with col_btn1:
                if st.form_submit_button("保存", type="primary"):
                    update_data = {
                        "ai_tags": new_tags,
                        "my_review": new_review,
                        "my_score": new_score,
                    }
                    # 更新データをバックエンドに送信
                    patch_res = requests.patch(f"{API_URL}/manga/manga/{target['id']}", json=update_data)
                    if patch_res.status_code == 200:
                        st.success("保存しました！")
                        # UIに即時反映させるため、セッション状態の漫画情報も更新
                        for idx, m in enumerate(st.session_state["search_results"]):
                            if m['id'] == target['id']:
                                st.session_state["search_results"][idx].update(update_data)
                        st.session_state["edit_target"] = None
                        st.rerun()
            with col_btn2:
                if st.form_submit_button("閉じる"):
                    st.session_state["edit_target"] = None
                    st.rerun()
