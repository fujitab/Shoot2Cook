# Pythonの公式イメージをベースにする (バージョンはプロジェクトに合わせる)
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピーしてインストール
# (Poetryを使わない場合は requirements.txt を使う)
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY main.py /app/
COPY prompt.txt /app/
COPY mock_response_text.txt /app/
# または全てのファイルをコピーする場合は次のようにします
# COPY . /app/

# 一時ディレクトリの作成
RUN mkdir -p /app/temp_uploads
RUN mkdir -p /app/temp_test_images

# Uvicornを起動するコマンド
# Renderを使用する場合はダッシュボードで設定するため、コメントアウトのままでOK
# ローカルで使用する場合は以下をコメント解除
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Renderは通常PORT環境変数を設定するので、それに追従する場合は以下を使用
# CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]