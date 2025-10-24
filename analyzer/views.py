from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .models import StoredString
from .serializers import StoredStringSerializer
import hashlib
import re


class StringAnalyzeView(APIView):
    def post(self, request):
        """POST /strings - Create and analyze string"""
        value = request.data.get("value")

        if value is None:
            return Response(
                {"detail": "Missing 'value' field."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(value, str):
            return Response(
                {"detail": "'value' must be a string."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        sha = hashlib.sha256(value.encode("utf-8")).hexdigest()
        if StoredString.objects.filter(pk=sha).exists():
            return Response(
                {"detail": "String already exists."},
                status=status.HTTP_409_CONFLICT
            )

        try:
            stored = StoredString(value=value)
            stored.save()
            serializer = StoredStringSerializer(stored)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {"detail": "String already exists."},
                status=status.HTTP_409_CONFLICT
            )


class StringDetailView(APIView):
    def get(self, request, string_value):
        """GET /strings/{string_value} - Get specific string"""
        sha = hashlib.sha256(string_value.encode("utf-8")).hexdigest()
        obj = get_object_or_404(StoredString, pk=sha)
        serializer = StoredStringSerializer(obj)
        return Response(serializer.data)

    def delete(self, request, string_value):
        """DELETE /strings/{string_value} - Delete string"""
        sha = hashlib.sha256(string_value.encode("utf-8")).hexdigest()
        obj = get_object_or_404(StoredString, pk=sha)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StringListView(APIView):
    def get(self, request):
        """GET /strings - Get all strings with filtering"""
        queryset = StoredString.objects.all()
        
        # Apply filters
        params = request.query_params
        
        # Filter logic (same as your get_queryset but for regular queryset)
        def to_bool(val):
            if val is None:
                return None
            return str(val).lower() in ["true", "1", "yes", "on"]

        is_palindrome = params.get("is_palindrome")
        if is_palindrome is not None:
            bool_val = to_bool(is_palindrome)
            if bool_val is not None:
                queryset = queryset.filter(properties__is_palindrome=bool_val)

        min_length = params.get("min_length")
        if min_length is not None:
            try:
                queryset = queryset.filter(properties__length__gte=int(min_length))
            except (ValueError, TypeError):
                pass

        max_length = params.get("max_length")
        if max_length is not None:
            try:
                queryset = queryset.filter(properties__length__lte=int(max_length))
            except (ValueError, TypeError):
                pass

        word_count = params.get("word_count")
        if word_count is not None:
            try:
                queryset = queryset.filter(properties__word_count=int(word_count))
            except (ValueError, TypeError):
                pass

        contains_char = params.get("contains_character")
        if contains_char and len(contains_char) == 1:
            queryset = queryset.filter(properties__character_frequency_map__has_key=contains_char)

        serializer = StoredStringSerializer(queryset, many=True)
        
        # Extract applied filters
        applied_filters = {}
        if params.get("is_palindrome"):
            applied_filters["is_palindrome"] = params.get("is_palindrome")
        if params.get("min_length"):
            applied_filters["min_length"] = params.get("min_length")
        if params.get("max_length"):
            applied_filters["max_length"] = params.get("max_length")
        if params.get("word_count"):
            applied_filters["word_count"] = params.get("word_count")
        if params.get("contains_character"):
            applied_filters["contains_character"] = params.get("contains_character")

        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "filters_applied": applied_filters
        })


class NaturalLanguageFilterView(APIView):
    def get(self, request):
        """GET /strings/filter-by-natural-language - Natural language filtering"""
        query = request.query_params.get("query")
        if not query:
            return Response(
                {"detail": "Query parameter 'query' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        text = query.lower()
        filters = {}

        if "palindrome" in text:
            filters["is_palindrome"] = "true"

        if "single" in text or "one" in text:
            filters["word_count"] = "1"

        match = re.search(r"longer than\s+(\d+)", text)
        if match:
            filters["min_length"] = str(int(match.group(1)) + 1)

        match = re.search(r"containing the letter\s+(\w)", text)
        if match:
            filters["contains_character"] = match.group(1)

        if not filters:
            return Response(
                {"detail": "Unable to parse natural language query."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Apply filters
        queryset = StoredString.objects.all()
        
        if "is_palindrome" in filters:
            queryset = queryset.filter(properties__is_palindrome=True)
        if "word_count" in filters:
            queryset = queryset.filter(properties__word_count=int(filters["word_count"]))
        if "min_length" in filters:
            queryset = queryset.filter(properties__length__gte=int(filters["min_length"]))
        if "contains_character" in filters:
            queryset = queryset.filter(properties__character_frequency_map__has_key=filters["contains_character"])

        serializer = StoredStringSerializer(queryset, many=True)
        
        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "interpreted_query": {
                "original": query,
                "parsed_filters": filters
            }
        })
