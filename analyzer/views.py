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
            return Response({"detail": "Missing 'value' field."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(value, str):
            return Response({"detail": "'value' must be a string."},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        sha = hashlib.sha256(value.encode("utf-8")).hexdigest()
        if StoredString.objects.filter(pk=sha).exists():
            return Response({"detail": "String already exists."},
                            status=status.HTTP_409_CONFLICT)

        try:
            stored = StoredString(value=value)
            stored.save()
            serializer = self.get_serializer(stored)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({"detail": "Duplicate string."},
                            status=status.HTTP_409_CONFLICT)

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
        # Apply filters by using filter_queryset
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        # Track which filters were actually applied
        applied_filters = {}
        params = request.query_params
        
        # Check each filter parameter and see if it was valid
        if params.get("is_palindrome"):
            try:
                # If we can convert it to bool, it was applied
                bool_val = str(params.get("is_palindrome")).lower() in ["true", "1", "yes"]
                applied_filters["is_palindrome"] = params.get("is_palindrome")
            except:
                pass

        if params.get("min_length"):
            try:
                int(params.get("min_length"))
                applied_filters["min_length"] = params.get("min_length")
            except:
                pass

        if params.get("max_length"):
            try:
                int(params.get("max_length"))
                applied_filters["max_length"] = params.get("max_length")
            except:
                pass

        if params.get("word_count"):
            try:
                int(params.get("word_count"))
                applied_filters["word_count"] = params.get("word_count")
            except:
                pass

        if params.get("contains_character"):
            char_val = params.get("contains_character")
            if char_val and len(char_val) == 1:
                applied_filters["contains_character"] = char_val

        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "filters_applied": applied_filters
        })

    def get_queryset(self):
        """Apply filters to the queryset"""
        queryset = super().get_queryset()
        params = self.request.query_params

        # is_palindrome filter
        is_palindrome = params.get("is_palindrome")
        if is_palindrome is not None:
            try:
                bool_val = str(is_palindrome).lower() in ["true", "1", "yes", "on"]
                queryset = queryset.filter(properties__is_palindrome=bool_val)
            except (ValueError, TypeError):
                pass  # Invalid boolean value, skip this filter

        # min_length filter
        min_length = params.get("min_length")
        if min_length is not None:
            try:
                min_val = int(min_length)
                queryset = queryset.filter(properties__length__gte=min_val)
            except (ValueError, TypeError):
                pass  # Invalid integer, skip this filter

        # max_length filter
        max_length = params.get("max_length")
        if max_length is not None:
            try:
                max_val = int(max_length)
                queryset = queryset.filter(properties__length__lte=max_val)
            except (ValueError, TypeError):
                pass  # Invalid integer, skip this filter

        # word_count filter
        word_count = params.get("word_count")
        if word_count is not None:
            try:
                count_val = int(word_count)
                queryset = queryset.filter(properties__word_count=count_val)
            except (ValueError, TypeError):
                pass  # Invalid integer, skip this filter

        # contains_character filter
        contains_char = params.get("contains_character")
        if contains_char is not None and len(contains_char) == 1:
            # Check if character exists in frequency map
            queryset = queryset.filter(properties__character_frequency_map__has_key=contains_char)

        return queryset

    @action(detail=False, methods=["get"], url_path="filter-by-natural-language")
    def filter_by_natural_language(self, request):
        query = request.query_params.get("query")
        if not query:
            return Response({"detail": "Query parameter is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        text = query.lower()
        filters = {}

        if "palindrome" in text:
            filters["is_palindrome"] = "true"

        if "single" in text or "one" in text:
            filters["word_count"] = "1"

        match = re.search(r"longer than (\d+)", text)
        if match:
            filters["min_length"] = str(int(match.group(1)) + 1)

        match = re.search(r"containing the letter (\w)", text)
        if match:
            filters["contains_character"] = match.group(1)

        if not filters:
            return Response({"detail": "Unable to parse natural language query."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Apply filters using the same logic as get_queryset
        from django.http import QueryDict
        query_dict = QueryDict('', mutable=True)
        for key, value in filters.items():
            query_dict[key] = value

        # Temporarily replace query_params to use get_queryset logic
        original_params = self.request.query_params
        self.request.query_params = query_dict
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "data": serializer.data,
                "count": len(serializer.data),
                "interpreted_query": {
                    "original": query,
                    "parsed_filters": filters
                }
            })
        finally:
            self.request.query_params = original_params
