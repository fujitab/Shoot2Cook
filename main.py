from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import shutil
import os
import google.generativeai as genai
from dotenv import load_dotenv
import re

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

        prompt_parts = [
            user_prompt, # プロンプト案4のテキスト部分
            uploaded_image, # アップロードした画像
        ]



        # 実際にAPIを呼び出す代わりに、テスト用のレスポンスを返す
        # テスト用のレスポンスを返す
        with open("mock_response_text.txt", "r", encoding="utf-8") as f:
            generated_text = f.read()
            return generated_text
        response = ""


        # レシピを生成
        # response = await model.generate_content_async(prompt_parts) # 非同期で呼び出す場合
        # レスポンスのテキストを取得
        generated_text = ""
        if response.parts:
            for part in response.parts:
                generated_text += part.text
            return generated_text
        elif hasattr(response, 'text'):
            generated_text = response.text
        else:
            generated_text = "---ERROR_NO_TEXT_IN_RESPONSE---"
            print(f"Warning: レスポンスにテキストが含まれていません。レスポンス: {response}")

    except Exception as e:
        print(f"Gemini APIとの連携中にエラーが発生しました: {e}")
        return f"---ERROR_API_CALL_FAILED---Error: {str(e)}"




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

        # プロンプトを読み込む
        with open("prompt.txt", "r", encoding="utf-8") as f:
            user_prompt_text = f.read()
            # デバッグ用
            print("デバッグ：", user_prompt_text)

        # AI関数を呼び出し (非同期で呼び出す場合は await をつける)
        raw_gemini_response_text = await generate_recipe_from_image_with_gemini(file_path, user_prompt_text) # もしAI関数がasyncなら

        # AIからの区切り文字付きテキストをパースする
        parsed_data = parse_custom_format_to_json_structure(raw_gemini_response_text)

        return parsed_data

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


# 食材リストのパース
def parse_identified_ingredients(text_block: str) -> list[dict]:
    """
    食材リストのテキストブロックをパースして、辞書のリストを返す。
    例："食材名:エリンギ|確信度:0.X" -> {"name": "エリンギ", "confidence": 0.X}
    """
    ingredients = []
    if not text_block:
        return ingredients
    
    for line in text_block.strip().splitlines(): # 改行で分割
        line = line.strip() # 前後の空白を削除
        if not line: # 空行はスキップ
            continue
        
        try:
            # 食材名と確信度を抽出
            parts = line.split("|")
            if len(parts) == 2:
                name_part = parts[0].spolit(':', 1)[1].strip()
                confidence_part = float(parts[1].split(':', 1)[1].strip())
                ingredients.append({"name": name_part, "confidence": confidence_part})
            else:
                print(f"Warning: 食材リストの形式が不正です: {line}")
        except Exception as e:
            print("Warning: 食材リストの行パース中にエラー：{line}, error: {e}")
            
    return ingredients


def parse_recipe_block(recipe_block_text: str, category_tag: str) -> dict | None:
    """
    単一のレシピブロックテキストをパースして、レシピ情報の辞書を返す。
    パースに失敗した場合は None を返すか、エラー情報を内包した辞書を返すこともできる。
    """
    recipe_data = {"categoryTag": category_tag} # カテゴリ名は引数で受け取る

    # 料理名
    name_match = re.search(r"料理名:(.*?)\n", recipe_block_text, re.DOTALL)
    if name_match:
        recipe_data["name"] = name_match.group(1).strip()
    else:
        print(f"Warning: [{category_tag}] 料理名が見つかりません。")
        return None # 必須項目がなければパース失敗とする

    # 分量 (servingsDescription)
    servings_match = re.search(r"分量:(.*?)\n", recipe_block_text, re.DOTALL)
    if servings_match:
        recipe_data["servingsDescription"] = servings_match.group(1).strip()
    else:
        recipe_data["servingsDescription"] = "（1人分）" # デフォルト値

    # 前提条件 (prerequisites)
    prerequisites_match = re.search(r"前提条件:(.*?)\n", recipe_block_text, re.DOTALL)
    if prerequisites_match:
        prereq_text = prerequisites_match.group(1).strip()
        recipe_data["prerequisites"] = prereq_text if prereq_text else "" # 空なら空文字
    else:
        recipe_data["prerequisites"] = ""


    # ---INGREDIENTS_START--- から ---INGREDIENTS_END--- までを抽出・パース
    ingredients_block_match = re.search(r"---INGREDIENTS_START---(.*?)---INGREDIENTS_END---", recipe_block_text, re.DOTALL)
    ingredients_list = []
    if ingredients_block_match:
        ingredients_text = ingredients_block_match.group(1).strip()
        for line in ingredients_text.splitlines():
            line = line.strip()
            if not line: continue
            parts = line.split('|')
            if len(parts) == 3:
                ingredients_list.append({
                    "name": parts[0].strip(),
                    "amount": parts[1].strip(),
                    "cost": parts[2].strip()
                })
            else:
                print(f"Warning: [{category_tag} - {recipe_data.get('name')}] 材料の行形式が不正です: {line}")
    recipe_data["ingredients"] = ingredients_list

    # 総費用 (totalCostEstimate)
    total_cost_match = re.search(r"総費用:(.*?)\n", recipe_block_text, re.DOTALL)
    if total_cost_match:
        recipe_data["totalCostEstimate"] = total_cost_match.group(1).strip()

    # ---NUTRITION_START--- から ---NUTRITION_END--- までを抽出・パース
    nutrition_block_match = re.search(r"---NUTRITION_START---(.*?)---NUTRITION_END---", recipe_block_text, re.DOTALL)
    nutrition_data = {}
    if nutrition_block_match:
        nutrition_text = nutrition_block_match.group(1).strip()
        for line in nutrition_text.splitlines():
            line = line.strip()
            if not line: continue
            parts = line.split(':', 1)
            if len(parts) == 2:
                nutrition_data[parts[0].strip()] = parts[1].strip() # キーをそのまま使う (後で変換しても良い)
            else:
                print(f"Warning: [{category_tag} - {recipe_data.get('name')}] 栄養情報の行形式が不正です: {line}")
    recipe_data["nutritionEstimate"] = nutrition_data


    # ---INSTRUCTIONS_START--- から ---INSTRUCTIONS_END--- までを抽出・パース
    instructions_block_match = re.search(r"---INSTRUCTIONS_START---(.*?)---INSTRUCTIONS_END---", recipe_block_text, re.DOTALL)
    instructions_list = []
    if instructions_block_match:
        instructions_text = instructions_block_match.group(1).strip()
        for line in instructions_text.splitlines():
            line = line.strip()
            if not line: continue
            # "1. ステップ1" のような形式を想定し、"." 以降を取得
            # もっと複雑な番号付けに対応するなら、正規表現で数字とドットを削除するなど
            if ". " in line:
                instructions_list.append(line.split(". ", 1)[1])
            else: # 番号なしの場合もそのまま追加（AIが必ずしも番号を振るとは限らない）
                instructions_list.append(line)

    recipe_data["instructions"] = instructions_list

    # 調理時間 (estimatedTime)
    time_match = re.search(r"調理時間:(.*?)\n", recipe_block_text, re.DOTALL)
    if time_match:
        recipe_data["estimatedTime"] = time_match.group(1).strip()

    # 洗い物 (dishwashingItems)
    dishwashing_match = re.search(r"洗い物:(.*?)\n", recipe_block_text, re.DOTALL)
    if dishwashing_match:
        recipe_data["dishwashingItems"] = dishwashing_match.group(1).strip()


    # ---POINTS_START--- から ---POINTS_END--- までを抽出・パース
    points_block_match = re.search(r"---POINTS_START---(.*?)---POINTS_END---", recipe_block_text, re.DOTALL)
    points_list = []
    if points_block_match:
        points_text = points_block_match.group(1).strip()
        for line in points_text.splitlines():
            line = line.strip()
            if not line: continue
            # "• おすすめポイント1" のような形式を想定し、"• " を削除
            if line.startswith("• "):
                points_list.append(line[2:])
            else: # 箇条書き記号がない場合もそのまま追加
                points_list.append(line)
    recipe_data["points"] = points_list

    return recipe_data
            
        


def parse_custom_format_to_json_structure(text_response: str) -> dict:
    """
    Gemini APIから返されたカスタム区切り文字付きテキストを解析し、
    クライアントに返すためのJSON構造（Python辞書）に変換する。
    """
    final_data = {
        "identifiedIngredients": [],
        "recipes": []
    }

    # 1. 食材リストのパース
    ingredients_match = re.search(r"---IDENTIFIED_INGREDIENTS_START---(.*?)---IDENTIFIED_INGREDIENTS_END---", text_response, re.DOTALL)
    if ingredients_match:
        ingredients_block_text = ingredients_match.group(1)
        final_data["identifiedIngredients"] = parse_identified_ingredients(ingredients_block_text)
    else:
        print("Warning: 食材リストのブロックが見つかりませんでした。")

    # 2. 各レシピブロックのパース
    # re.finditer を使うと、マッチした全ての箇所を順番に処理できる
    recipe_pattern = r"---RECIPE_START:(.*?)---(.*?)---RECIPE_END---"
    for match in re.finditer(recipe_pattern, text_response, re.DOTALL):
        category_tag_from_match = match.group(1).strip()
        recipe_block_content = match.group(2).strip() # ---RECIPE_END--- の直前まで

        # recipe_block_content の中で、さらに各詳細情報をパースする
        parsed_recipe = parse_recipe_block(recipe_block_content, category_tag_from_match)
        if parsed_recipe:
            final_data["recipes"].append(parsed_recipe)
        else:
            print(f"Warning: カテゴリ '{category_tag_from_match}' のレシピブロックのパースに失敗しました。")

    if not final_data["identifiedIngredients"] and not final_data["recipes"]:
        # 何もパースできなかった場合は、エラーを示すか、特別なレスポンスを返す
        print("Error: 有効な食材リストもレシピもパースできませんでした。")
        # クライアントにはAIの生レスポンスを見せるか、汎用エラーを返す
        # ここでは例として、パース失敗を示す情報を返す
        return {"error": "AIからの応答を解析できませんでしたが、有効なデータがありませんでした。", "raw_response_snippet": text_response[:500]}


    return final_data
