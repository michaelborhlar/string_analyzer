from django.urls import path
from .views import StringAnalyzeView, StringDetailView, StringListView, NaturalLanguageFilterView

urlpatterns = [
    path('strings', StringAnalyzeView.as_view(), name='create-string'),
    path('strings/<str:string_value>', StringDetailView.as_view(), name='string-detail'),
    path('strings', StringListView.as_view(), name='list-strings'),
    path('strings/filter-by-natural-language', NaturalLanguageFilterView.as_view(), name='natural-language-filter'),
]
