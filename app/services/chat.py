"""
大規模言語モデル(LLM)との対話に関するビジネスロジックを処理するサービスクラス。
LangGraphで構築されたグラフ(Agent)を操作します。
"""
from langchain_core.messages import HumanMessage, AIMessage
from app.graph.nodes import llm
from app.graph.workflows import tool_llm_graph

class LLMService:
    """LLMサービスのクラス"""
    def __init__(self):
        """
        コンストラクタ。
        LangGraphで定義されたLLMやグラフをインスタンス変数として保持します。
        """
        self.llm = llm
        self.tool_llm_graph = tool_llm_graph
    
    async def chat(self, thread_id: str, message: str) -> str:
        """
        ユーザーからのメッセージを受け取り、LangGraphエージェントを実行して応答を生成します。
        スレッドIDごとに会話の状態を管理します。

        Args:
            thread_id (str): 会話を一意に識別するスレッドID。
            message (str): ユーザーからのメッセージ。

        Returns:
            str: AIアシスタントからの最終的な応答メッセージ。
        """
        # スレッドIDをコンフィグに設定
        config = {"configurable": {"thread_id": thread_id}}
        # 入力メッセージを作成
        inputs = {"messages": [HumanMessage(content=message)]}
        # グラフ(Agent)を非同期で実行
        response = await self.tool_llm_graph.ainvoke(inputs, config=config)
        # 最後のメッセージ（AIの応答）を返す
        return response["messages"][-1].content
    
    async def get_found_manga_ids(self, thread_id: str) -> list[int]:
        """
        指定されたスレッドIDの会話状態から、見つかった漫画のIDリストを取得します。

        Args:
            thread_id (str): 会話のスレッドID。

        Returns:
            list[int]: 見つかった漫画IDのリスト。
        """
        config = {"configurable": {"thread_id": thread_id}}
        state = await tool_llm_graph.aget_state(config)
        found_manga_ids = state.values.get("found_manga_ids", [])
        return found_manga_ids
    
    async def get_search_queries(self, thread_id: str) -> list[str]:
        """
        指定されたスレッドIDの会話状態から、生成された検索クエリのリストを取得します。

        Args:
            thread_id (str): 会話のスレッドID。

        Returns:
            list[str]: 生成された検索クエリのリスト。
        """
        config = {"configurable": {"thread_id": thread_id}}
        state = await tool_llm_graph.aget_state(config)
        search_queries = state.values.get("search_queries", [])
        return search_queries
    
    def chat_with_context(self, message: str, context: str) -> str:
        """
        シンプルなコンテキストを与えて、LLMからの応答を取得します。
        （主にAgentが内部でツールとして利用する想定など）

        Args:
            message (str): ユーザーからのメッセージ。
            context (str): 事前に与えるコンテキスト情報。

        Returns:
            str: LLMからの応答。
        """
        response = self.llm.invoke([
            AIMessage(content=context),
            HumanMessage(content=message)
        ])
        return response.content