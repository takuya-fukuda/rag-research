from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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
        return Response({"message": "Hello from the backend!"})
    
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
    

class DataRegsiter(APIView):
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

            # データベースに保存
            DataTable.objects.create(
                chunks=chunk,
                embeddings=embedding,
                metadata={"source": "PDF", "file_name": pdf_file.name}
            )

        return Response({"message": "Data registered successfully."}, status=status.HTTP_201_CREATED)
