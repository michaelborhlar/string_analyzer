from rest_framework import serializers
from .models import StoredString

class StoredStringSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredString
        fields = ['id', 'value', 'properties', 'created_at']
        read_only_fields = ['id', 'properties', 'created_at']
