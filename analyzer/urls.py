from django.urls import path
from .views import StringsView, StringDetailView, NaturalLanguageFilterView

urlpatterns = [
    # Single endpoint for both POST (create) and GET (list with filters)
    path('strings', StringsView.as_view(), name='strings'),
    path('strings/<str:string_value>', StringDetailView.as_view(), name='string-detail'),
    path('strings/filter-by-natural-language', NaturalLanguageFilterView.as_view(), name='natural-language-filter'),
]
