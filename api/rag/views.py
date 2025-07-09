from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from api.rag.authentication import RefreshJWTAuthentication  # カスタム認証クラス

import os
from .models import DataTable
import fitz  # PyMuPDF

from openai import OpenAI

#LangChain
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

#mcp
import json
import asyncio
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import mcp
from langchain_mcp_adapters.tools import load_mcp_tools


from dotenv import load_dotenv
load_dotenv()

# LangChainで会話用インスタンス生成
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    openai_api_key=os.getenv("OPENAI_API_KEY")  # .envや環境変数で設定
)

# グローバル辞書でユーザごとのメモリを管理
memory_map = {}

# ベクトル
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ノーマルのAIチャット。ただし、データの学習はされない。
class NormalChat(APIView):
    authentication_classes = [JWTAuthentication]  # 認証クラスを無効化
    permission_classes = []  # 権限クラスを無効化
    def get(self, request, fromat=None):
        return Response({"message": "Postでリクエストしてください"})
    
    def post(self, request, format=None):
        user_id = request.data.get("user_id", "default_user")  # ユーザIDを取得、デフォルトは"default_user"

        # ユーザごとのメモリを保持
        if user_id not in memory_map:
            memory_map[user_id] = ConversationBufferMemory(return_messages=True)

        memory = memory_map[user_id]
        conversation = ConversationChain(llm=llm, memory=memory)

        question = request.data.get("question", "")
        answer = conversation.predict(input=question)

        return Response({"question": question, "answer": answer})

# RAGを使用したAIチャット
class RagChat(APIView):
    authentication_classes = [JWTAuthentication]  # 認証クラスを無効化
    permission_classes = []  # 権限クラスを無効化
    def get(self, request, fromat=None):
        return Response({"message": "Postでリクエストしてください"})
    
    def post(self, request, format=None):
        question = request.data.get("question", "")
        user_id = request.data.get("user_id", "default_user")  # ユーザIDを取得、デフォルトは"default_user"
        if not question:
            return Response({"error": "No question provided."}, status=status.HTTP_400_BAD_REQUEST)
        # ユーザごとのメモリを保持
        if user_id not in memory_map:
            memory_map[user_id] = ConversationBufferMemory(return_messages=True)

        memory = memory_map[user_id]
        conversation = ConversationChain(llm=llm, memory=memory)     


        try:
            embedding = client.embeddings.create(
                model="text-embedding-3-small",
                input=question
            ).data[0].embedding

            # ベクトル検索。上位3件を取得。
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, chunks, metadata FROM data_table ORDER BY embeddings <#> %s::vector LIMIT 3",
                    [embedding]
                )
                rows = cursor.fetchall()
            retrieved_texts = "\n\n".join([row[1] for row in rows])
            prompt = f"""以下は質問に対する参考文書です。\n\n{retrieved_texts}\n\n質問: {question}\n\nこれに基づいて回答してください。参照できるドキュメントがない場合は、わかりませんと答えてください。"""

            # ConversationChainにプロンプトとして入力（履歴も自動で考慮）
            answer = conversation.predict(input=prompt)

            # 回答を返却
            return Response({
                "question": question,
                "answer": answer,
                "references": [row[2] for row in rows],  # metadata一覧を返却
            })
        
        except Exception as e:
            return Response(
                {"error": f"処理中にエラーが発生しました: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# RAGのデータ登録用API（現在PDFのみ対応）
class DataRegisiter(APIView):
    authentication_classes = [JWTAuthentication]  # 認証クラスを無効化
    permission_classes = []  # 権限クラスを無効化

    def get(self, request, fromat=None):
        return Response({"message": "Postでリクエストしてください"})

    def post(self, request, format=None):
        #PDFファイルの取得
        pdf_file = request.FILES.get("file")
        if not pdf_file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        #PDFファイルの読み込み
        try:
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        except Exception as e:
            return Response({"error": f"Failed to read PDF file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        #PDFからテキストを抽出
        text = ""
        for page in doc:
            text += page.get_text()

        # テキストをチャンクに分割
        split_text = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=100)
        chunks = split_text.split_text(text) #リスト

        for chunk in chunks:
            # OpenAIのembeddingsを生成
            embedding = client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk
            ).data[0].embedding

            # データベースに保存。DB結果を返さないので、Serializerを使用しない
            DataTable.objects.create(
                chunks=chunk,
                embeddings=embedding,
                metadata={"source": "PDF", "file_name": pdf_file.name}
            )

        return Response({"message": "Data registered successfully."}, status=status.HTTP_201_CREATED)

class MCPAgentView(APIView):
    authentication_classes = [JWTAuthentication]  # 認証クラスを無効化
    permission_classes = []  # 権限クラスを無効化

    def get(self, request, fromat=None):
        return Response({"message": "Postでリクエストしてください"})
    
    def post(self, request):
        question = request.data.get("question", "")
        if not question:
            return Response({"error": "No question provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            response_data = asyncio.run(self.invoke_agent(question))

            response_text = ""
            for message in response_data["messages"]:
                message_dict = dict(message)
                if message_dict.get("type") == "ai":
                    content = message_dict.get("content", "")
                    if content.strip():
                        response_text = content
                        break
            return Response({"result": response_text}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def invoke_agent(self, question):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        notion_token = os.getenv("MCP_SECRET")

        if not openai_api_key or not notion_token:
            raise EnvironmentError("OPENAI_API_KEY または MCP_SECRET が設定されていません")
        
        mcp_headers = json.dumps({
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28"
        })
        
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={"OPENAPI_MCP_HEADERS": mcp_headers}
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                tools = await load_mcp_tools(session)
                agent = create_react_agent("openai:gpt-4o", tools=tools)
                response = await agent.ainvoke({
                    "messages": [{"role": "user", "content": question}]
                })
                return response        


# ログイン処理
class LoginView(APIView):
    authentication_classes = [JWTAuthentication]  # 認証クラスを無効化
    permission_classes = []  # 権限クラスを無効化

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data.get("access", None)
        refresh = serializer.validated_data.get("refresh", None)
        if access:
            response = Response(status=status.HTTP_200_OK)
            max_age = settings.COOKIE_TIME
            response.set_cookie('access', access, max_age=max_age, httponly=True, samesite='Lax')
            response.set_cookie('refresh', refresh, max_age=max_age, httponly=True, samesite='Lax')

            return response
        
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

# トークン再発行処理
class RetryView(APIView):
    authentication_classes = [RefreshJWTAuthentication]  # 認証クラスを無効化
    permission_classes = []  # 権限クラスを無効化

    def post(self, request):
        request.data['refresh'] = request.META.get('HTTP_REFRESH_TOKEN')
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data.get("access", None)
        refresh = serializer.validated_data.get("refresh", None)
        if access:
            response = Response(status=status.HTTP_200_OK)
            max_age = settings.COOKIE_TIME
            response.set_cookie('access', access, max_age=max_age, httponly=True, samesite='Lax')
            response.set_cookie('refresh', refresh, max_age=max_age, httponly=True, samesite='Lax')

            return response
        
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    
# ログアウト処理
class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        response = Response(status=status.HTTP_200_OK)
        response.delete_cookie('access')
        response.delete_cookie('refresh')
        return response