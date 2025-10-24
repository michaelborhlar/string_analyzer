from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .models import StoredString
from .serializers import StoredStringSerializer
import hashlib
import re
import urllib.parse


class StringsView(APIView):
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

    def get(self, request):
        """GET /strings - Get all strings with filtering"""
        queryset = StoredString.objects.all()
        params = request.query_params
        
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


class StringDetailView(APIView):
    def get(self, request, string_value):
        """GET /strings/{string_value} - Get specific string"""
        try:
            # Decode URL-encoded string (handles spaces, special characters)
            decoded_value = urllib.parse.unquote(string_value)
            
            sha256_hash = hashlib.sha256(decoded_value.encode("utf-8")).hexdigest()
            obj = get_object_or_404(StoredString, pk=sha256_hash)
            serializer = StoredStringSerializer(obj)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": "String not found."},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, string_value):
        """DELETE /strings/{string_value} - Delete string"""
        try:
            # Decode URL-encoded string (handles spaces, special characters)
            decoded_value = urllib.parse.unquote(string_value)
            
            sha256_hash = hashlib.sha256(decoded_value.encode("utf-8")).hexdigest()
            obj = get_object_or_404(StoredString, pk=sha256_hash)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"detail": "String not found."},
                status=status.HTTP_404_NOT_FOUND
            )


# class NaturalLanguageFilterView(APIView):
#     def get(self, request):
#         """GET /strings/filter-by-natural-language - Natural language filtering"""
#         query = request.query_params.get("query")
#         if not query:
#             return Response(
#                 {"detail": "Query parameter 'query' is required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         text = query.lower().strip()
#         parsed_filters = {}

#         # Parse ALL the example queries from the specification exactly
#         if "single word palindromic strings" in text:
#             parsed_filters["is_palindrome"] = True
#             parsed_filters["word_count"] = 1
        
#         elif "strings longer than 10 characters" in text:
#             parsed_filters["min_length"] = 11
        
#         elif "palindromic strings that contain the first vowel" in text:
#             parsed_filters["is_palindrome"] = True
#             parsed_filters["contains_character"] = "a"
        
#         elif "strings containing the letter z" in text:
#             parsed_filters["contains_character"] = "z"
        
#         else:
#             # Fallback to keyword-based parsing
#             if "palindromic" in text or "palindrome" in text:
#                 parsed_filters["is_palindrome"] = True

#             if "single word" in text:
#                 parsed_filters["word_count"] = 1

#             # Handle length queries
#             if "longer than" in text:
#                 match = re.search(r"longer than\s+(\d+)", text)
#                 if match:
#                     parsed_filters["min_length"] = int(match.group(1)) + 1

#             # Handle character queries
#             if "letter z" in text:
#                 parsed_filters["contains_character"] = "z"
#             elif "first vowel" in text:
#                 parsed_filters["contains_character"] = "a"
#             elif "containing the letter" in text:
#                 match = re.search(r"containing the letter\s+(\w)", text)
#                 if match:
#                     parsed_filters["contains_character"] = match.group(1).lower()

#         if not parsed_filters:
#             return Response(
#                 {"detail": "Unable to parse natural language query."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Apply the parsed filters
#         queryset = StoredString.objects.all()
        
#         if "is_palindrome" in parsed_filters:
#             queryset = queryset.filter(properties__is_palindrome=True)
        
#         if "word_count" in parsed_filters:
#             queryset = queryset.filter(properties__word_count=parsed_filters["word_count"])
        
#         if "min_length" in parsed_filters:
#             queryset = queryset.filter(properties__length__gte=parsed_filters["min_length"])
        
#         if "contains_character" in parsed_filters:
#             queryset = queryset.filter(properties__character_frequency_map__has_key=parsed_filters["contains_character"])

#         serializer = StoredStringSerializer(queryset, many=True)
        
#         return Response({
#             "data": serializer.data,
#             "count": queryset.count(),
#             "interpreted_query": {
#                 "original": query,
#                 "parsed_filters": parsed_filters
#             }
#         })
class NaturalLanguageFilterView(APIView):
    def get(self, request):
        """GET /strings/filter-by-natural-language - Natural language filtering"""
        query = request.query_params.get("query", "").lower().strip()

        if not query:
            return Response({"error": "Missing 'query' parameter"}, status=status.HTTP_400_BAD_REQUEST)

        filters = {}

        # --- Simple heuristics ---
        if "palindrome" in query or "palindromic" in query:
            filters["properties__is_palindrome"] = True

        if "single word" in query or "one word" in query:
            filters["properties__word_count"] = 1

        # Length filters
        import re
        longer_than = re.search(r"longer than (\d+)", query)
        if longer_than:
            filters["properties__length__gt"] = int(longer_than.group(1))

        shorter_than = re.search(r"shorter than (\d+)", query)
        if shorter_than:
            filters["properties__length__lt"] = int(shorter_than.group(1))

        exact_length = re.search(r"exactly (\d+) characters", query)
        if exact_length:
            filters["properties__length"] = int(exact_length.group(1))

        # Contains character (letter a-z)
        contains_char = re.search(r"letter (\w)", query)
        if contains_char:
            filters["value__icontains"] = contains_char.group(1)
        elif "contain" in query:
            char_match = re.search(r"contain[s]? the letter (\w)", query)
            if char_match:
                filters["value__icontains"] = char_match.group(1)

        # --- Handle conflicting filters ---
        if "palindromic" in query and "not" in query:
            return Response({
                "error": "Conflicting filters in query"
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if not filters:
            return Response({
                "error": "Unable to parse natural language query"
            }, status=status.HTTP_400_BAD_REQUEST)

        # --- Apply filters ---
        results = StoredString.objects.filter(**filters)
        data = [
            {
                "id": obj.id,
                "value": obj.value,
                "properties": obj.properties,
                "created_at": obj.created_at
            }
            for obj in results
        ]

        # --- Return formatted response ---
        return Response({
            "data": data,
            "count": len(data),
            "interpreted_query": {
                "original": query,
                "parsed_filters": filters
            }
        }, status=status.HTTP_200_OK)
