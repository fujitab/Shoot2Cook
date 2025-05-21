from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import shutil
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv() # .envファイルを読み込む

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEYが設定されていません。.envファイルを確認してください。")

genai.configure(api_key=GOOGLE_API_KEY) # SDKにAPIキーを設定（身分証提出みたいな）

app = FastAPI()

# アップロードされたファイルを保存する一時的なディレクトリを作成（もしなければ）
UPLOAD_DIR = "temp_uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Gemini
MODEL_NAME = "gemini-2.0-flash"

# geminiapiのテスト用関数
async def test_gemini_api(image_path: str, user_prompt: str):
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        uploaded_image = genai.upload_file(path=image_path)

        prompt_parts = [
            user_prompt,
            uploaded_image,
        ]

        response = await model.generate_content_async(prompt_parts)

        # レスポンス構造をチェックする
        if response.parts:
            generated_text = ""
            for part in response.parts:
                generated_text += part.text
            return generated_text
        else:
            return "レスポンスが空です。"
    except Exception as e:
        return f"エラーが発生しました: {e}"
    finally:
        pass

# test_gemini_apiの呼び出し
@app.get("/test-gemini-api/")
async def test_gemini_api_endpoint():
    try:
        image_path = "temp_test_images/IMG_0583.jpeg"
        # prompt.txtファイルからプロンプトを読み込む
        with open("prompt.txt", "r", encoding="utf-8") as f:
            user_prompt = f.read()
        result = await test_gemini_api(image_path, user_prompt)
        return {"result": result}
    except Exception as e:
        return {"error": f"エラーが発生しました: {e}"}
    finally:
        pass



async def generate_recipe_from_image_with_gemini(image_path: str, user_prompt: str):
    """
    指定された画像とプロンプトを使って、Gemini APIからレシピを生成する関数。
    """
    try:
        # マルチモーダルモデルのインスタンスを作成
        model = genai.GenerativeModel(MODEL_NAME)

        # アップロードされた画像を準備
        uploaded_image = genai.upload_file(path=image_path)

        # プロンプトと画像を組み合わせたコンテンツを作成
        # プロンプト案4 をベースに、画像とテキストを渡す
        # ここでは user_prompt はプロンプト案4のテキスト部分全体を想定
        prompt_parts = [
            user_prompt, # プロンプト案4のテキスト部分
            uploaded_image, # アップロードした画像
        ]

        # レシピを生成 (レスポンス形式をJSONにするようプロンプトで指示している前提)
        response = await model.generate_content_async(prompt_parts) # 非同期で呼び出す場合
        # response = model.generate_content(prompt_parts) # 同期で呼び出す場合 (FastAPIのasync def内では非同期が望ましいが、SDKの挙動による)

        # 生成されたテキスト (JSON文字列であることを期待) を取得
        # response.text にJSON文字列が入っていることを想定
        # 実際には response オブジェクトの構造を確認して、適切な部分からテキストを取り出す
        if response.parts:
            # response.parts がリストの場合、最初のテキスト部分を取得するなどの処理が必要
            # モデルやSDKのバージョンによって response の構造が変わる可能性があるので注意
            generated_text = ""
            for part in response.parts:
                generated_text += part.text
            return generated_text
        else:
            return "レスポンスが空です。"
    except Exception as e:
        return f"エラーが発生しました: {e}"

    finally:
        # アップロードした一時ファイルを削除 (SDKが自動で管理している場合や、
        # 別の方法で一時ファイルを扱っている場合は不要なこともある)
        if 'uploaded_image' in locals() and hasattr(uploaded_image, 'name'):
             try:
                 # genai.delete_file(uploaded_image.name) # 一時ファイルを削除するAPIがあるか確認
                 pass # ここではSDKの挙動に依存するため、一旦何もしない
             except Exception as e_del:
                 print(f"一時ファイルの削除中にエラー: {e_del}")





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
        # 画像を一時保存
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            # デバッグ用
            print("デバッグ：アップロードされたファイル名:", image.filename)

        # AIにレシピ生成を依頼
        # プロンプト案4のテキスト部分をここに用意する (長くなるので別途変数にするか、ファイルから読み込むのが良い)
        with open("prompt.txt", "r", encoding="utf-8") as f:
            user_prompt_text = f.read()
            # デバッグ用
            print("デバッグ：", user_prompt_text)

        # AI関数を呼び出し (非同期で呼び出す場合は await をつける)
        gemini_response = await generate_recipe_from_image_with_gemini(file_path, user_prompt_text) # もしAI関数がasyncなら
        # gemini_response = generate_recipe_from_image_with_gemini(file_path, user_prompt_text)
        print("デバッグ：", gemini_response)
        # return {"result": gemini_response}

        # Gemini APIからのレスポンス (JSON文字列であることを期待) をそのまま返す
        # クライアント側でJSONとしてパースしてもらう
        # もしPythonの辞書型で返したい場合は、AI関数側でjson.loadsするか、
        # ここで gemini_response (が文字列なら) をjson.loadsする。
        # FastAPIは辞書型を返すと自動でJSONレスポンスにしてくれる。
        # return json.loads(gemini_response) # gemini_response がJSON文字列の場合
        if isinstance(gemini_response, str): # もし文字列で返ってきたら
            
            import json
            try:
                recipe_data = json.loads(gemini_response)
                return recipe_data
            
            except json.JSONDecodeError as e:
                print(f"JSONパースエラー: {e}")
                print(f"元の文字列: {gemini_response}")
                return {"error": "AIからの応答を解析できませんでした。"}
                # JSONとしてパースできなかった場合は、エラーとして元のテキストを返すか、
        #         # ログに記録してエラーレスポンスを返す
        #         print(f"Warning: GeminiからのレスポンスがJSONとしてパースできませんでした: {gemini_response}")
        #         return {"error": "AIからの応答を解析できませんでした。", "raw_response": gemini_response}
        # return gemini_response # すでに辞書型ならそのまま返す


    except Exception as e:
        print(f"エンドポイント処理中にエラー: {e}") # エラーログ
        # 本番ではもっと詳細なエラー情報（スタックトレースなど）をログに出力する
        # クライアントには汎用的なエラーメッセージを返す
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"レシピの生成中にサーバーでエラーが発生しました。")

    finally:
        await image.close()
        # 一時保存したファイルを削除 (必要に応じて)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"一時ファイル '{file_path}' を削除しました。")
            except Exception as e_del_file:
                print(f"一時ファイル '{file_path}' の削除中にエラー: {e_del_file}")