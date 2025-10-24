from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .models import StoredString
from .serializers import StoredStringSerializer
import hashlib
import re


class StoredStringViewSet(viewsets.ModelViewSet):
    queryset = StoredString.objects.all()
    serializer_class = StoredStringSerializer
    lookup_field = "value"

    def create(self, request, *args, **kwargs):
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
            serializer = self.get_serializer(stored)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response(
                {"detail": "String already exists."},
                status=status.HTTP_409_CONFLICT
            )

    def retrieve(self, request, value=None):
        sha = hashlib.sha256(value.encode("utf-8")).hexdigest()
        obj = get_object_or_404(StoredString, pk=sha)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def destroy(self, request, value=None):
        sha = hashlib.sha256(value.encode("utf-8")).hexdigest()
        obj = get_object_or_404(StoredString, pk=sha)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        # FIXED: Extract single values for filters_applied, not lists
        applied_filters = {}
        params = request.query_params
        
        if params.get('is_palindrome'):
            applied_filters['is_palindrome'] = params.get('is_palindrome')
        if params.get('min_length'):
            applied_filters['min_length'] = params.get('min_length')
        if params.get('max_length'):
            applied_filters['max_length'] = params.get('max_length')
        if params.get('word_count'):
            applied_filters['word_count'] = params.get('word_count')
        if params.get('contains_character'):
            applied_filters['contains_character'] = params.get('contains_character')

        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "filters_applied": applied_filters  # Now with single values instead of lists
        })

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        def to_bool(val):
            if val is None:
                return None
            return str(val).lower() in ["true", "1", "yes", "on"]

        def to_int(val):
            try:
                return int(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        # Apply is_palindrome filter
        is_palindrome = params.get("is_palindrome")
        if is_palindrome is not None:
            bool_value = to_bool(is_palindrome)
            if bool_value is not None:
                qs = qs.filter(properties__is_palindrome=bool_value)

        # Apply min_length filter
        min_length = params.get("min_length")
        if min_length is not None:
            min_val = to_int(min_length)
            if min_val is not None:
                qs = qs.filter(properties__length__gte=min_val)

        # Apply max_length filter
        max_length = params.get("max_length")
        if max_length is not None:
            max_val = to_int(max_length)
            if max_val is not None:
                qs = qs.filter(properties__length__lte=max_val)

        # Apply word_count filter
        word_count = params.get("word_count")
        if word_count is not None:
            count_val = to_int(word_count)
            if count_val is not None:
                qs = qs.filter(properties__word_count=count_val)

        # Apply contains_character filter
        contains_char = params.get("contains_character")
        if contains_char is not None and len(contains_char) == 1:
            qs = qs.filter(properties__character_frequency_map__has_key=contains_char)

        return qs

    @action(detail=False, methods=["get"], url_path="filter-by-natural-language")
    def filter_by_natural_language(self, request):
        query = request.query_params.get("query")
        if not query:
            return Response(
                {"detail": "Query parameter 'query' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        text = query.lower()
        filters = {}

        # Parse palindrome queries
        if "palindrome" in text or "palindromic" in text:
            filters["is_palindrome"] = "true"

        # Parse word count queries
        if "single word" in text or "one word" in text:
            filters["word_count"] = "1"
        elif "two words" in text:
            filters["word_count"] = "2"
        elif "three words" in text:
            filters["word_count"] = "3"

        # Parse length queries
        length_match = re.search(r"longer than\s+(\d+)", text)
        if length_match:
            filters["min_length"] = str(int(length_match.group(1)) + 1)

        length_match = re.search(r"shorter than\s+(\d+)", text)
        if length_match:
            filters["max_length"] = str(int(length_match.group(1)) - 1)

        # Parse character queries
        char_match = re.search(r"contain[s]?\s+(?:the\s+)?letter\s+(\w)", text)
        if not char_match:
            char_match = re.search(r"has\s+(?:the\s+)?letter\s+(\w)", text)
        if char_match:
            filters["contains_character"] = char_match.group(1).lower()

        # Handle "first vowel" case
        if "first vowel" in text:
            filters["contains_character"] = "a"

        if not filters:
            return Response(
                {"detail": "Unable to parse natural language query."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Apply the parsed filters
        from django.http import QueryDict
        query_dict = QueryDict('', mutable=True)
        for key, value in filters.items():
            query_dict[key] = value

        # Use get_queryset with the parsed filters
        original_params = self.request.query_params
        self.request.query_params = query_dict
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                "data": serializer.data,
                "count": queryset.count(),
                "interpreted_query": {
                    "original": query,
                    "parsed_filters": filters
                }
            })
        finally:
            self.request.query_params = original_params
