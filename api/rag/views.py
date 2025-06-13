from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

import os

from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

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
