import mcp
import requests
import json

mcp = mcp.server.fastmcp.FastMCP("mcp-server-example")

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

@mcp.tool()
def ask_information(word: str) -> str:
    match word:
        case "なごや個人開発者の集い":
            answer = "毎週日曜日に開催する定例オフライン開発会です。 ソフト・ハードのエンジニアだけでなく、デザイナー、クリエイター、マーケターの方々が集い、もくもく作業するもよし、開発・制作の相談をするもよし、単に作品の自慢をするもよし、協力してプロダクトを作るもよし"
        case _:
            answer = "不明"
    return answer

# RAGのベクトル検索
# @mcp.tool()
# def rag_search_api(question: str, user_id: str = "default_user") -> str:
#     try:
#         url = "http://localhost:8000/api/rag/ragchat/"
#         payload = {
#             "question": question,
#             "user_id": user_id
#         }
#         headers = {"Content-Type": "application/json"}
#         response = requests.post(url, data=json.dumps(payload), headers=headers)

#         if response.status_code == 200:
#             data = response.json()
#             if "error" in data:
#                 return f"エラー: {data['error']}"
#             return data.get("answer", "回答なし")
#         else:
#             return f"APIエラー: {response.status_code} - {response.text}"

#     except Exception as e:
#         return f"エラー: {str(e)}"
    
if __name__ == "__main__":
    mcp.run(transport="stdio")