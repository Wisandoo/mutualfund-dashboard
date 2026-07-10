from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FundFactSheetViewSet

router = DefaultRouter()
router.register(r'ffs', FundFactSheetViewSet, basename='ffs')

urlpatterns = [
    path('', include(router.urls)),
]