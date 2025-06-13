from rest_framework.views import APIView
from rest_framework.response import Response

# Create your views here.
class Backend(APIView):
    def get(self, request, fromat=None):
        return Response({"message": "Hello from the backend!"})
