# 1. ベースイメージ（スリム版Pythonで軽量化）
FROM python:3.12-slim

# 2. ワークディレクトリの設定
WORKDIR /app

# 3. システムの依存パッケージ（SQLiteなど）のインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. 依存ライブラリのコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリケーションコードのコピー
COPY . .

# 6. ポートの開放（FastAPI: 8000, Streamlit: 8501）
EXPOSE 8000 8501

# 7. 起動スクリプトの実行
# FastAPIをバックグラウンドで起動し、Streamlitをフォアグラウンドで起動
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 & streamlit run webui.py --server.port 8501 --server.address 0.0.0.0"]