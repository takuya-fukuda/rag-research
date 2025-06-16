from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import os
from .models import DataTable
import fitz  # PyMuPDF

from openai import OpenAI

#LangChain
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

# Create your views here.
class NormalChat(APIView):
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

class RagChat(APIView):
    def get(self, request, fromat=None):
        return Response({"message": "Postでリクエストしてください"})
    
    def post(self, request, format=None):
        question = request.data.get("question", "")
        if not question:
            return Response({"error": "No question provided."}, status=status.HTTP_400_BAD_REQUEST)
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
            prompt = f"""以下は質問に対する参考文書です。\n\n{retrieved_texts}\n\n質問: {question}\n\nこれに基づいて回答してください。"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "あなたは親切なアシスタントです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            answer = response.choices[0].message.content.strip()
            # ④ 回答を返却
            return Response({
                "question": question,
                "answer": answer,
                "references": [row[2] for row in rows],  # metadata一覧を返却
            })
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DataRegsiter(APIView):
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
