from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import shutil
import os

app = FastAPI()

# アップロードされたファイルを保存する一時的なディレクトリを作成（もしなければ）
UPLOAD_DIR = "temp_uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.get("/")
async def read_root():
    return {"message": "こんにちは、ズボラAIレシピのバックエンドです！"}

@app.get("/users/{user_id}")
async def read_user(user_id: int):
    return {"user_id": user_id, "message": f"ユーザーID: {user_id} の情報です。"}


@app.get("/items/")
async def read_items(skip: int = 0, limit: int = 10): # デフォルト値を指定できる
    fake_items_db = [{"item_name": "リンゴ"}, {"item_name": "バナナ"}, {"item_name": "オレンジ"}]
    return {"items": fake_items_db[skip : skip + limit], "skip": skip, "limit": limit}

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


@app.post("/items/")
async def create_item(item: Item):
    return {"item_name": item.name, "price_with_tax": item.price + (item.tax or 0)}


# 冷蔵庫の画像をアップロードするエンドポイント
@app.post("/upload-refrigerator-image/")
async def upload_refrigerator_image(image: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, image.filename)
    try:
        with open(file_path, "wb") as buffer: # バッファにファイルを書き込む
            shutil.copyfileobj(image.file, buffer) 
        return {"filename": image.filename, "content_type": image.content_type, "message": f"ファイル '{image.filename}' が '{UPLOAD_DIR}' に保存されました。"}
    except Exception as e:
        return {"error": f"ファイルのアップロード中にエラーが発生しました: {e}"}
    finally:
        await image.close()