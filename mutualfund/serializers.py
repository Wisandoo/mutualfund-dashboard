from rest_framework import serializers
from .models import FundFactSheet

class FundFactSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundFactSheet
        fields = '__all__'