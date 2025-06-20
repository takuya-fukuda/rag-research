import mcp

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

if __name__ == "__main__":
    mcp.run(transport="stdio")