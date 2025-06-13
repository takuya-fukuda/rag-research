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

memory = ConversationBufferMemory(return_messages=True)

conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True,
)

# Create your views here.
class NormalChat(APIView):
    def get(self, request, fromat=None):
        return Response({"message": "Hello from the backend!"})
    
    def post(self, request, format=None):
        question = request.data.get("question")
        if not question:
            return Response({"error": "questionフィールドが必要です"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            answer = conversation.predict(input=question)
            return Response({"question": question, "answer": answer})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
