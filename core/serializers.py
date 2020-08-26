from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from core.block_verifier import user_verifier

from core.models import *


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all())])
    organization = serializers.CharField()
    first_name=serializers.CharField()

    def create(self, validated_data):
        request = self.context.get("request")
        if(user_verifier(validated_data, request)):
            error = {'message': "User request is blocked"}
            raise serializers.ValidationError(error)

        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            organization=validated_data['organization'],
            first_name=validated_data['first_name']
        )
        user.set_password(validated_data['password'])
        user.save()

        # when user is created, link to all existing demo flights
        for demo_flight in Flight.objects.filter(is_demo=True).all():
            user.demo_flights.add(demo_flight)

        return user

    class Meta:
        model = User
        fields = ["pk", 'username', 'email', 'is_staff', 'password', 'type', 'organization' , 'first_name']


class FlightSerializer(serializers.ModelSerializer):
    nodeodm_info = serializers.SerializerMethodField()

    def get_nodeodm_info(self, flight):
        return flight.get_nodeodm_info()

    class Meta:
        model = Flight
        fields = ["uuid", "name", "user", "date", "camera", "annotations", "state", "nodeodm_info", "processing_time",
                  "is_demo", "deleted"]


class ArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artifact
        fields = ["pk", "type", "project", "name", "type"]


class UserProjectSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault())
    flights = serializers.PrimaryKeyRelatedField(many=True,
                                                 queryset=Flight.objects.all())
    artifacts = serializers.PrimaryKeyRelatedField(many=True,
                                                   queryset=Artifact.objects.all())

    def create(self, validated_data):
        flights = validated_data.pop("flights")
        artifacts = validated_data.pop("artifacts")
        proj = UserProject.objects.create(**validated_data)
        proj.flights.set(flights)
        proj.artifacts.set(artifacts)
        proj._create_geoserver_proj_workspace()
        return proj

    class Meta:
        model = UserProject
        fields = ['uuid', 'user', 'flights', 'artifacts', "name", "description", "is_demo", "deleted"]

class BlockCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockCriteria
        fields = ["pk", "type", "value", "ip"]