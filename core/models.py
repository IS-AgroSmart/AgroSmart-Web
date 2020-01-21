import json
import os

from django.db import models
from django.contrib.auth.models import AbstractUser
from enum import Enum
import uuid as u

from django.db.models.signals import post_save, post_delete

import requests
from requests.auth import HTTPBasicAuth


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
    demo_flights = models.ManyToManyField('Flight', related_name='demo_users')


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
    ERROR = "Error"


class Flight(models.Model):
    uuid = models.UUIDField(primary_key=True, default=u.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    is_demo = models.BooleanField(default=False)
    name = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    camera = models.CharField(max_length=10, choices=[(tag.name, tag.value) for tag in Camera])
    multispectral_processing = models.BooleanField(default=False)
    annotations = models.TextField()
    deleted = models.BooleanField(default=False)
    state = models.CharField(max_length=10,
                             choices=[(tag.name, tag.value) for tag in FlightState],
                             default=FlightState.WAITING)
    processing_time = models.PositiveIntegerField(default=0)

    def get_nodeodm_info(self):
        if self.state != FlightState.PROCESSING.name:
            return {}

        data = requests.get("http://localhost:3000/task/" + str(self.uuid) + "/info").json()
        return {"processingTime": data.get("processingTime", 0), "progress": data.get("progress", 0),
                "numImages": data.get("imagesCount", 0)}

    def get_thumbnail_path(self):
        return "./tmp/" + str(self.uuid) + "_thumbnail.png"

    def _get_geoserver_ws_name(self):
        return "flight_" + str(self.uuid)

    def create_geoserver_workspace_and_upload_geotiff(self):
        requests.post("http://localhost/geoserver/geoserver/rest/workspaces",
                      headers={"Content-Type": "application/json"},
                      data='{"workspace": {"name": "' + self._get_geoserver_ws_name() + '"}}',
                      auth=HTTPBasicAuth('admin', 'geoserver'))
        requests.put(
            "http://localhost/geoserver/geoserver/rest/workspaces/" + self._get_geoserver_ws_name() + "/coveragestores/ortho/external.geotiff",
            headers={"Content-Type": "text/plain"},
            data="file:///media/input/" + str(self.uuid) + "/odm_orthophoto/odm_orthophoto.tif",
            auth=HTTPBasicAuth('admin', 'geoserver'))


def create_nodeodm_task(sender, instance, created, **kwargs):
    if created:
        requests.post('http://localhost:3000/task/new/init',
                      headers={"set-uuid": str(instance.uuid)},
                      files={
                          "name": (None, instance.name),
                          "webhook": (None, "http://localhost:8000/api/webhook-processing-complete"),
                          "options": (
                              None, json.dumps([{"name": "dsm", "value": True}, {"name": "time", "value": True}])
                          )
                      })


def link_demo_flight_to_active_users(sender, instance, created, **kwargs):
    if created and instance.is_demo:
        for user in User.objects.filter(is_active=True).all():
            user.demo_flights.add(instance)


def delete_nodeodm_task(sender, instance, **kwargs):
    requests.post("http://localhost:3000/task/remove",
                  headers={'Content-Type': "application/x-www-form-urlencoded"},
                  data="uuid=" + str(instance.uuid), )


def delete_geoserver_workspace(sender, instance, **kwargs):
    querystring = {"recurse": "true"}
    requests.delete("http://localhost/geoserver/geoserver/rest/workspaces/flight_" + str(instance.uuid),
                    params=querystring,
                    auth=HTTPBasicAuth('admin', 'geoserver'))


def delete_thumbnail(sender, instance, **kwargs):
    if os.path.exists(instance.get_thumbnail_path()):
        os.remove(instance.get_thumbnail_path())


post_save.connect(create_nodeodm_task, sender=Flight)
post_save.connect(link_demo_flight_to_active_users, sender=Flight)
post_delete.connect(delete_nodeodm_task, sender=Flight)
post_delete.connect(delete_thumbnail, sender=Flight)
post_delete.connect(delete_geoserver_workspace, sender=Flight)


class ArtifactType(Enum):
    ORTHOMOSAIC = "Orthomosaic"
    SHAPEFILE = "Shapefile"


class Artifact(models.Model):
    type = models.CharField(max_length=20, choices=[(tag.name, tag.value) for tag in ArtifactType])
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="artifacts")
