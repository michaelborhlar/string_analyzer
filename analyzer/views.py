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
    """
    ViewSet for the String Analyzer API.
    Handles create, retrieve, list (with filtering),
    delete, and natural language filtering.
    """
    queryset = StoredString.objects.all()
    serializer_class = StoredStringSerializer
    lookup_field = "value"  # allows using string value in URL

    # POST /strings/ → create and analyze string
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

    # GET /strings/{value}/ → get specific string
    def retrieve(self, request, value=None):
        sha = hashlib.sha256(value.encode("utf-8")).hexdigest()
        obj = get_object_or_404(StoredString, pk=sha)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    # DELETE /strings/{value}/ → delete string
    def destroy(self, request, value=None):
        sha = hashlib.sha256(value.encode("utf-8")).hexdigest()
        obj = StoredString.objects.filter(pk=sha).first()
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET /strings/?filters... → filter results
    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        def to_bool(val):
            return str(val).lower() in ["1", "true", "yes"]

        if "is_palindrome" in params:
            qs = qs.filter(properties__is_palindrome=to_bool(params["is_palindrome"]))

        if "min_length" in params:
            qs = qs.filter(properties__length__gte=int(params["min_length"]))

        if "max_length" in params:
            qs = qs.filter(properties__length__lte=int(params["max_length"]))

        if "word_count" in params:
            qs = qs.filter(properties__word_count=int(params["word_count"]))

        if "contains_character" in params:
            qs = qs.filter(properties__character_frequency_map__has_key=params["contains_character"])

        return qs

    # GET /strings/filter-by-natural-language/?query=...
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

        match = re.search(r"longer than (\\d+)", text)
        if match:
            filters["min_length"] = str(int(match.group(1)) + 1)

        match = re.search(r"containing the letter (\\w)", text)
        if match:
            filters["contains_character"] = match.group(1)

        if not filters:
            return Response({"detail": "Unable to parse natural language query."},
                            status=status.HTTP_400_BAD_REQUEST)

        # apply filters using get_queryset
        self.request._request.GET = filters
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
