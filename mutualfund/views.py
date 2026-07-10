from rest_framework import viewsets
from .models import FundFactSheet
from .serializers import FundFactSheetSerializer

class FundFactSheetViewSet(viewsets.ModelViewSet):
    queryset = FundFactSheet.objects.all()
    serializer_class = FundFactSheetSerializer