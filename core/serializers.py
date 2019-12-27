from rest_framework import serializers

from core.models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["pk", 'username', 'email', 'is_staff']


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = ["uuid", "name", "user", "date", "camera", "annotations", "state"]
