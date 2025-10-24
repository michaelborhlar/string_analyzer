from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .models import StoredString
from .serializers import StoredStringSerializer
import hashlib
import re


class CreateStringView(APIView):
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

        sha256_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
        
        # Check if string already exists
        if StoredString.objects.filter(pk=sha256_hash).exists():
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
        sha256_hash = hashlib.sha256(string_value.encode("utf-8")).hexdigest()
        obj = get_object_or_404(StoredString, pk=sha256_hash)
        serializer = StoredStringSerializer(obj)
        return Response(serializer.data)

    def delete(self, request, string_value):
        """DELETE /strings/{string_value} - Delete string"""
        sha256_hash = hashlib.sha256(string_value.encode("utf-8")).hexdigest()
        obj = get_object_or_404(StoredString, pk=sha256_hash)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StringListView(APIView):
    def get(self, request):
        """GET /strings - Get all strings with filtering"""
        queryset = StoredString.objects.all()
        params = request.query_params
        
        # Track applied filters
        applied_filters = {}
        
        # Apply is_palindrome filter
        is_palindrome = params.get("is_palindrome")
        if is_palindrome is not None:
            try:
                bool_val = str(is_palindrome).lower() in ["true", "1", "yes", "on"]
                queryset = queryset.filter(properties__is_palindrome=bool_val)
                applied_filters["is_palindrome"] = is_palindrome
            except:
                pass

        # Apply min_length filter
        min_length = params.get("min_length")
        if min_length is not None:
            try:
                min_val = int(min_length)
                queryset = queryset.filter(properties__length__gte=min_val)
                applied_filters["min_length"] = min_length
            except:
                pass

        # Apply max_length filter
        max_length = params.get("max_length")
        if max_length is not None:
            try:
                max_val = int(max_length)
                queryset = queryset.filter(properties__length__lte=max_val)
                applied_filters["max_length"] = max_length
            except:
                pass

        # Apply word_count filter
        word_count = params.get("word_count")
        if word_count is not None:
            try:
                count_val = int(word_count)
                queryset = queryset.filter(properties__word_count=count_val)
                applied_filters["word_count"] = word_count
            except:
                pass

        # Apply contains_character filter
        contains_char = params.get("contains_character")
        if contains_char is not None and len(contains_char) == 1:
            queryset = queryset.filter(properties__character_frequency_map__has_key=contains_char)
            applied_filters["contains_character"] = contains_char

        serializer = StoredStringSerializer(queryset, many=True)
        
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
        parsed_filters = {}

        # Parse natural language queries
        if "palindrome" in text or "palindromic" in text:
            parsed_filters["is_palindrome"] = True

        if "single word" in text or "one word" in text:
            parsed_filters["word_count"] = 1

        # Handle length queries
        length_match = re.search(r"longer than\s+(\d+)", text)
        if length_match:
            parsed_filters["min_length"] = int(length_match.group(1)) + 1

        # Handle character queries
        char_match = re.search(r"contain[s]?\s+(?:the\s+)?(?:letter\s+)?(\w)", text)
        if char_match:
            parsed_filters["contains_character"] = char_match.group(1).lower()

        # Handle specific cases from examples
        if "first vowel" in text:
            parsed_filters["contains_character"] = "a"
        elif "letter z" in text:
            parsed_filters["contains_character"] = "z"

        if not parsed_filters:
            return Response(
                {"detail": "Unable to parse natural language query."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Apply the parsed filters
        queryset = StoredString.objects.all()
        
        if "is_palindrome" in parsed_filters:
            queryset = queryset.filter(properties__is_palindrome=parsed_filters["is_palindrome"])
        if "word_count" in parsed_filters:
            queryset = queryset.filter(properties__word_count=parsed_filters["word_count"])
        if "min_length" in parsed_filters:
            queryset = queryset.filter(properties__length__gte=parsed_filters["min_length"])
        if "contains_character" in parsed_filters:
            queryset = queryset.filter(properties__character_frequency_map__has_key=parsed_filters["contains_character"])

        serializer = StoredStringSerializer(queryset, many=True)
        
        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "interpreted_query": {
                "original": query,
                "parsed_filters": parsed_filters
            }
        })
