from rest_framework.routers import DefaultRouter
from .views import StoredStringViewSet

router = DefaultRouter()
router.register(r"strings", StoredStringViewSet, basename="strings")

urlpatterns = router.urls
