from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, CompanyViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("companies", CompanyViewSet)

urlpatterns = [path("", include(router.urls))]
