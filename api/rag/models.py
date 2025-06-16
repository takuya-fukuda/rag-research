from django.db import models
from pgvector.django import VectorField

# Create your models here.
class DataTable(models.Model):
    id = models.AutoField(primary_key=True)
    chunks = models.TextField(blank=True, null=True)  # チャンクデータを保存
    embeddings = VectorField(dimensions=1536)  # OpenAIのembeddingsの次元数に合わせる
    metadata = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        db_table = 'data_table' #Adminで参照時data_tableと表示される