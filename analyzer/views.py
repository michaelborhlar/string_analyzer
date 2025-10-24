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
        # Handle raw JSON data directly to avoid any parser issues
        if hasattr(request, 'data'):
            value = request.data.get('value')
        else:
            # Fallback for raw data
            import json
            try:
                data = json.loads(request.body)
                value = data.get('value')
            except:
                value = None

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
        # Apply filters
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        # SAFE filter extraction - ensure no list values
        applied_filters = {}
        params = request.query_params
        
        # Extract single values safely
        for key in ['is_palindrome', 'min_length', 'max_length', 'word_count', 'contains_character']:
            value = params.get(key)
            if value is not None:
                # Ensure we get a string, not a list
                if isinstance(value, list) and len(value) > 0:
                    applied_filters[key] = value[0]
                else:
                    applied_filters[key] = value
        
        # Ensure response is exactly as expected
        response_data = {
            "data": serializer.data,
            "count": queryset.count(),
            "filters_applied": applied_filters
        }
        
        # Validate no list values remain
        self._validate_no_lists(response_data)
        
        return Response(response_data)

    def _validate_no_lists(self, data):
        """Recursively check that no lists exist in the response"""
        if isinstance(data, list):
            raise ValueError("Found list in response data")
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    raise ValueError(f"List found at key '{key}': {value}")
                self._validate_no_lists(value)

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        
        # SAFE parameter extraction - handle both single values and lists
        def get_single_param(key):
            value = params.get(key)
            if isinstance(value, list) and len(value) > 0:
                return value[0]
            return value

        def to_bool(val):
            if val is None:
                return None
            if isinstance(val, list):
                if len(val) > 0:
                    val = val[0]
                else:
                    return None
            return str(val).lower() in ["true", "1", "yes", "on"]

        def to_int(val):
            try:
                if isinstance(val, list) and len(val) > 0:
                    val = val[0]
                return int(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        # Apply filters with safe parameter access
        is_palindrome = get_single_param("is_palindrome")
        if is_palindrome is not None:
            bool_val = to_bool(is_palindrome)
            if bool_val is not None:
                qs = qs.filter(properties__is_palindrome=bool_val)

        min_length = get_single_param("min_length")
        if min_length is not None:
            min_val = to_int(min_length)
            if min_val is not None:
                qs = qs.filter(properties__length__gte=min_val)

        max_length = get_single_param("max_length")
        if max_length is not None:
            max_val = to_int(max_length)
            if max_val is not None:
                qs = qs.filter(properties__length__lte=max_val)

        word_count = get_single_param("word_count")
        if word_count is not None:
            count_val = to_int(word_count)
            if count_val is not None:
                qs = qs.filter(properties__word_count=count_val)

        contains_char = get_single_param("contains_character")
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

        # Use safe parameter extraction
        if isinstance(query, list):
            query = query[0]

        text = query.lower()
        filters = {}

        # Your existing natural language logic...
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

        # Apply filters safely
        from django.http import QueryDict
        query_dict = QueryDict('', mutable=True)
        for key, value in filters.items():
            query_dict[key] = value

        original_params = self.request.query_params
        self.request.query_params = query_dict
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            response_data = {
                "data": serializer.data,
                "count": queryset.count(),
                "interpreted_query": {
                    "original": query,
                    "parsed_filters": filters
                }
            }
            
            # Validate no lists
            self._validate_no_lists(response_data)
            
            return Response(response_data)
        finally:
            self.request.query_params = original_params
