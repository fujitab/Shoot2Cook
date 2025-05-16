from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()

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


