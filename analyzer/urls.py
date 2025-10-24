# from django.urls import path
# from .views import StringAnalyzeView, StringDetailView, StringListView, NaturalLanguageFilterView

# urlpatterns = [
#     path('strings', StringAnalyzeView.as_view(), name='create-string'),
#     path('strings/<str:string_value>', StringDetailView.as_view(), name='string-detail'),
#     path('strings', StringListView.as_view(), name='list-strings'),
#     path('strings/filter-by-natural-language', NaturalLanguageFilterView.as_view(), name='natural-language-filter'),
# ]

from django.urls import path
from .views import (
    StringAnalyzeView,
    StringDetailView,
    StringListView,
    NaturalLanguageFilterView
)

urlpatterns = [
    # POST /strings/ → create new string
    path('strings/', StringAnalyzeView.as_view(), name='create-string'),

    # GET /strings/ → list all strings
    path('strings/all/', StringListView.as_view(), name='list-strings'),

    # GET or DELETE /strings/<id>/ → get or delete one string by hash id
    path('strings/<str:string_value>/', StringDetailView.as_view(), name='string-detail'),

    # GET /strings/filter-by-natural-language/?q=something
    path('strings/filter-by-natural-language/', NaturalLanguageFilterView.as_view(), name='natural-language-filter'),
]

