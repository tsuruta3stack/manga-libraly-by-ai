from langgraph.graph import StateGraph, START, END
from app.graph.nodes import State, chatbot_node, ranking_results_node, keyword_search_node, query_expansion_node, vector_search_node
from langgraph.checkpoint.memory import MemorySaver

workflow = StateGraph(State)

# ノードの登録
workflow.add_node("expander", query_expansion_node)
workflow.add_node("keyword_search", keyword_search_node)
workflow.add_node("vector_search", vector_search_node)
workflow.add_node("ranker", ranking_results_node)
workflow.add_node("chatbot", chatbot_node)

# # 流れの定義
workflow.set_entry_point("expander")
workflow.add_edge("expander", "vector_search")
workflow.add_edge("vector_search", "ranker")
workflow.add_edge("ranker", "chatbot")
workflow.add_edge("chatbot", END)
memory = MemorySaver()
tool_llm_graph = workflow.compile(checkpointer=memory)


