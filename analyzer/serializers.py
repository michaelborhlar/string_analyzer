from rest_framework import serializers
from .models import StoredString


class PropertiesSerializer(serializers.Serializer):
    """Serializer for the computed properties of a string."""
    length = serializers.IntegerField()
    is_palindrome = serializers.BooleanField()
    unique_characters = serializers.IntegerField()
    word_count = serializers.IntegerField()
    sha256_hash = serializers.CharField()
    character_frequency_map = serializers.DictField(child=serializers.IntegerField())


class StoredStringSerializer(serializers.ModelSerializer):
    """Main serializer for the StoredString model."""
    properties = PropertiesSerializer(read_only=True)
    value = serializers.CharField()

    class Meta:
        model = StoredString
        fields = ["id", "value", "properties", "created_at"]
        read_only_fields = ["id", "properties", "created_at"]

    def validate_value(self, value):
        """Ensure value is a non-empty string."""
        if not isinstance(value, str):
            raise serializers.ValidationError("Value must be a string.")
        if not value.strip():
            raise serializers.ValidationError("Value cannot be empty.")
        return value
