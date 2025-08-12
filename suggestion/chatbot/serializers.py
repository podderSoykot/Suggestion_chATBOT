from rest_framework import serializers
from .models import Place

class PlaceSerializer(serializers.ModelSerializer):
    distance = serializers.FloatField(read_only=True)  # will add this dynamically

    class Meta:
        model = Place
        fields = ['id', 'name', 'latitude', 'longitude', 'category', 'distance']
