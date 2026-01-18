"""
アプリケーション全体で使用する設定値を管理します。
PydanticのBaseSettingsを使用して、環境変数や.envファイルから設定を読み込みます。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    設定項目を定義するクラス。
    デフォルト値を持ち、環境変数で上書き可能です。
    """
    # プロバイダーのセット
    LLM_TYPE: str = "ollama"
    # Ollama APIのベースURL
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # 使用するOllamaのチャットモデル名
    OLLAMA_MODEL: str = "gemma3:12b"
    # 使用するOllamaの埋め込みモデル名
    OLLAMA_EMBEDDING_MODEL: str = "embeddinggemma"
    # OpenAI APIのキー
    OPENAI_API_KEY: Optional[str] = None
    # 使用するOpenAIのチャットモデル名
    OPENAI_MODEL: str = "gpt-4o-mini"
    # 使用するOpenAIの埋め込みモデル名
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    # SQLiteデータベースの接続URL
    SQLITE_URL: str = "sqlite:///./data/manga.db"
    # ChromaDBのデータ保存先ディレクトリ
    CHROMA_URL: str = "./data/chroma"

    # .envファイルから環境変数を読み込むための設定
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# 設定クラスのインスタンスを作成
settings = Settings()
