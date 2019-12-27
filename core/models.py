from django.db import models
from django.contrib.auth.models import AbstractUser
from enum import Enum
import uuid as u

from django.db.models.signals import post_save, post_delete

import requests


class UserType(Enum):
    DEMO_USER = "DemoUser"
    ACTIVE = "Active"
    DELETED = "Deleted"
    ADMIN = "Admin"


class User(AbstractUser):
    organization = models.CharField(max_length=20, blank=True)
    type = models.CharField(max_length=20,
                            choices=[(tag.name, tag.value) for tag in UserType],
                            default=UserType.DEMO_USER)


class BaseProject(models.Model):
    uuid = models.UUIDField(primary_key=True, default=u.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField()
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class DemoProject(BaseProject):
    users = models.ManyToManyField(User, related_name="demo_projects")
    flights = models.ManyToManyField("Flight", related_name="demo_projects")
    artifacts = models.ManyToManyField("Artifact", related_name="demo_projects")


class UserProject(BaseProject):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_projects")
    flights = models.ManyToManyField("Flight", related_name="user_projects")
    artifacts = models.ManyToManyField("Artifact", related_name="user_projects")


class Camera(Enum):
    REDEDGE = "Micasense RedEdge"
    RGB = "RGB"


class FlightState(Enum):
    WAITING = "Waiting for images"
    PROCESSING = "Processing"
    COMPLETE = "Complete"
    PAUSED = "Paused"
    CANCELED = "Canceled"


class Flight(models.Model):
    uuid = models.UUIDField(primary_key=True, default=u.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    date = models.DateField()
    camera = models.CharField(max_length=10, choices=[(tag.name, tag.value) for tag in Camera])
    multispectral_processing = models.BooleanField(default=False)
    annotations = models.TextField()
    deleted = models.BooleanField(default=False)
    state = models.CharField(max_length=10,
                             choices=[(tag.name, tag.value) for tag in FlightState],
                             default=FlightState.WAITING)


def create_nodeodm_task(sender, instance, created, **kwargs):
    if created:
        r = requests.post('http://localhost:3000/task/new/init',
                          headers={"set-uuid": str(instance.uuid)},
                          data={"name": instance.name})
        print("Created: " + r.text)


def delete_nodeodm_task(sender, instance, **kwargs):
    requests.post("http://localhost:3000/task/remove",
                  headers={'Content-Type': "application/x-www-form-urlencoded"},
                  data="uuid=" + str(instance.uuid), )


post_save.connect(create_nodeodm_task, sender=Flight)
post_delete.connect(delete_nodeodm_task, sender=Flight)


class ArtifactType(Enum):
    ORTHOMOSAIC = "Orthomosaic"
    SHAPEFILE = "Shapefile"


class Artifact(models.Model):
    type = models.CharField(max_length=20, choices=[(tag.name, tag.value) for tag in ArtifactType])
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="artifacts")
