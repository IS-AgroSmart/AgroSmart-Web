from rest_framework import serializers

from core.models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["pk", 'username', 'email', 'is_staff']


class FlightSerializer(serializers.ModelSerializer):
    nodeodm_info = serializers.SerializerMethodField()

    def get_nodeodm_info(self, flight):
        return flight.get_nodeodm_info()

    class Meta:
        model = Flight
        fields = ["uuid", "name", "user", "date", "camera", "annotations", "state", "nodeodm_info", "processing_time"]


class ArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artifact
        fields = ["pk", "type", "flight"]


class UserProjectSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all())
    flights = serializers.PrimaryKeyRelatedField(many=True,
        queryset=Flight.objects.all())
    artifacts = serializers.PrimaryKeyRelatedField(many=True,
        queryset=Artifact.objects.all())

    class Meta:
        model = UserProject
        fields = ['pk','user', 'flights', 'artifacts']