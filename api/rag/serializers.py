from rest_framework import serializers
from api.rag.models import DataTable

class DataTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataTable
        fields = '__all__'  # 全フィールドをシリアライズ
        #fields = ['id', 'chunks', 'embeddings', 'metadata']
        #read_only_fields = ['id']  # idは読み取り専用
        #extra_kwargs = {
        #    'chunks': {'required': True},
        #    'embeddings': {'required': True},
        #    'metadata': {'required': False, 'default': {}}
        #}