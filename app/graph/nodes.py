from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import START, END
from langgraph.graph.message import add_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from typing import TypedDict, Annotated, List, Optional
from pydantic import BaseModel, Field
from sqlmodel import Session
from app.core.config import settings
from app.models.manga import engine, MangaSearchKeywordParams, MangaSearchVectorParams, MangaForLLM, to_llm_data, get_llm_description
from app.services.manga import MangaService
from app.models.chroma import vectorDB

def merge_ids(old_lists: list[int], new_lists: Optional[list[int]] = None) -> list:
    return list(set((old_lists or []) + (new_lists or [])))

def add_ids(old_lists: list[int], new_lists: Optional[list[int]] = None) -> list:
    return list(((old_lists or []) + (new_lists or [])))

def merge_dicts(old_lists: list[dict], new_lists: Optional[list[dict]] = None) -> list[dict]:
    # IDをキーにして辞書にまとめることで重複を排除
    merged = {m["id"]: m for m in (old_lists or []+ new_lists or [])}
    return list(merged.values())

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    found_manga_ids: List[int]
    search_queries: List[str]
    llm_contexts: List[dict]
    next_step: str
    retry_count: int

def get_llm(model_type="ollama"):
    if model_type == "openai":
        return ChatOpenAI(
            model=settings.OPENAI_MODEL, 
            api_key=settings.OPENAI_API_KEY, # 環境変数から取得
            temperature=0
        )
    else:
        return ChatOllama(
            model=settings.OLLAMA_MODEL, 
            base_url=settings.OLLAMA_BASE_URL, 
            num_ctx=40960, 
            temperature=0
        )

llm = get_llm(settings.LLM_TYPE)

class SearchQueryExpansionOutput(BaseModel):
    search_queries: List[str] = Field(description="SQL検索用の単語")

def query_expansion_node(state: State):
    user_input = state["messages"][-1].content
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
         あなたは漫画データベースの検索クエリ生成の専門家です。ユーザーの要望を分析し、関連するキーワードを3〜5個生成してください。
         検索はキーワード検索とベクトル検索をどちらも行います。単語のみのキーワードと短文のキーワードの双方を織り交ぜてください。
         ユーザーの要望から漫画の持つ微妙なニュアンスを表現する多様なキーワードを生成してください。
         注意: 「〇〇の漫画」「〇〇漫画」というキーワードは絶対に作らないでください。
         """),
        ("human", "要望: {user_input}")
    ])

    chain = prompt | llm.with_structured_output(SearchQueryExpansionOutput)
    response_text = chain.invoke({"user_input": user_input})
    
    return {"search_queries": response_text.search_queries}


class RankingResultsOutput(BaseModel):
    ranking_ids: List[int] = Field(description="関連順に並んだ漫画のIDのリスト")
    
def ranking_results_node(state: State):
    user_input = state["messages"][-1].content
    llm_contexts = state.get("llm_contexts", [])
    contexts_description = get_llm_description(MangaForLLM)
    if not llm_contexts:
        return {"found_manga_ids": []}

    prompt = ChatPromptTemplate.from_messages([
        ("system", "あなたは漫画の目利きです。提示された漫画リストをユーザーの要望に合致している順に並び替えてください。"),
        ("human", "要望: \n{user_input}\n\n【検索結果】\n{contexts}\n\n【結果の見方】\n{contexts_description}")
    ])

    chain = prompt | llm.with_structured_output(RankingResultsOutput)
    response = chain.invoke({"user_input": user_input, "contexts": str(llm_contexts),"contexts_description": contexts_description})
    
    return {"found_manga_ids":response.ranking_ids[:5]}


class ChatbotOutput(BaseModel):
    answer: str = Field(description="ユーザーに答えるメッセージ")
    found_manga_ids: List[int] = Field(description="提示された漫画のIDのリスト、最大5つ")

def chatbot_node(state: State):
    contexts = str(state.get("llm_contexts", []))
    contexts_description = get_llm_description(MangaForLLM)
    user_input = state["messages"][-1].content
    history = state["messages"][-11:-1]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "あなたは情熱的な漫画コンシェルジュです。提供された漫画情報を参照し、ユーザーの要望に最適な作品を推薦してください。"),
        ("system", "おすすめする漫画は5つまでとし、メッセージと合わせてその5つのIDリストを出力してください。"),
        ("system", "メッセージにはおすすめする漫画のタイトルと推薦理由を含めてください。"),
        ("system", "ユーザーへの質疑は行わず回答のみ行ってください。提供された漫画の情報が不足している場合はそれを伝えてください"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "要望: \n{user_input}\n\n【検索結果】\n{contexts}\n\n【結果の見方】\n{contexts_description}")
    ])

    chain = prompt | llm.with_structured_output(ChatbotOutput)
    
    response = chain.invoke({
        "user_input": user_input,
        "contexts": contexts,
        "contexts_description": contexts_description,
        "history": history
    })

    answer = AIMessage(content = response.answer)
    found_manga_ids = response.found_manga_ids
    
    return {"messages": [answer], "found_manga_ids": found_manga_ids}

def keyword_search_node(state: State):
    queries = state.get("search_queries", [])
    all_found_ids = []
    llm_contexts = []
    with Session(engine) as session:
        manga_service = MangaService(session)
        for query in queries:
            manga_list = manga_service.get_manga_list_by_keyword(MangaSearchKeywordParams(keyword=query, limit=10))
            all_found_ids.extend([m.id for m in manga_list])
            llm_contexts.extend(to_llm_data(manga_list))
    return {
        "found_manga_ids": merge_ids(all_found_ids),
        "llm_contexts": merge_dicts(llm_contexts)
    }

def vector_search_node(state: State):
    queries = state.get("search_queries", [])
    all_found_ids = []
    llm_contexts = []
    with Session(engine) as session:
        manga_service = MangaService(session, vectorDB)
        for query in queries:
            manga_list = manga_service.get_manga_list_by_vector(MangaSearchVectorParams(keyword=query, limit=10))
            all_found_ids.extend([m.id for m in manga_list])
            llm_contexts.extend(to_llm_data(manga_list))
    return {
        "found_manga_ids": merge_ids(all_found_ids),
        "llm_contexts": merge_dicts(llm_contexts)
    }
