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

print(get_llm_description(MangaForLLM))