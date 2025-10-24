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
        obj = StoredString.objects.filter(pk=sha).first()
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        # FIX: Use filter_queryset to apply the filters from get_queryset()
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        # Extract applied filters properly
        applied_filters = {}
        params = request.query_params
        
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
            "count": queryset.count(),  # Use queryset.count() for efficiency
            "filters_applied": applied_filters
        })

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        def to_bool(val):
            if val is None:
                return None
            return str(val).lower() in ["1", "true", "yes"]

        # FIX: Use .get() instead of [] to avoid list access
        is_palindrome = params.get("is_palindrome")
        if is_palindrome is not None:
            qs = qs.filter(properties__is_palindrome=to_bool(is_palindrome))

        min_length = params.get("min_length")
        if min_length is not None:
            try:
                qs = qs.filter(properties__length__gte=int(min_length))
            except (ValueError, TypeError):
                pass

        max_length = params.get("max_length")
        if max_length is not None:
            try:
                qs = qs.filter(properties__length__lte=int(max_length))
            except (ValueError, TypeError):
                pass

        word_count = params.get("word_count")
        if word_count is not None:
            try:
                qs = qs.filter(properties__word_count=int(word_count))
            except (ValueError, TypeError):
                pass

        contains_char = params.get("contains_character")
        if contains_char and len(contains_char) == 1:
            qs = qs.filter(properties__character_frequency_map__has_key=contains_char)

        return qs

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

        queryset = self.get_queryset().filter(**{
            k: v for k, v in filters.items() if not k.startswith("contains_character")
        })

        if "contains_character" in filters:
            queryset = queryset.filter(properties__character_frequency_map__has_key=filters["contains_character"])

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "data": serializer.data,
            "count": len(serializer.data),
            "interpreted_query": {
                "original": query,
                "parsed_filters": filters
            }
        }, status=status.HTTP_200_OK)
