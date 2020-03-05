import json
import logging
import os
import shutil

from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from enum import Enum
import uuid as u

from django.db.models.signals import post_save, post_delete, m2m_changed

import requests
from django.dispatch import receiver
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
                            default=UserType.DEMO_USER.name)
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
    artifacts = models.ManyToManyField("Artifact", related_name="demo_projects", blank=True)


class UserProject(BaseProject):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_projects")
    flights = models.ManyToManyField("Flight", related_name="user_projects")
    artifacts = models.ManyToManyField("Artifact", related_name="user_projects", blank=True)
    must_create_workspace = models.BooleanField(default=True)

    def _get_geoserver_ws_name(self):
        return "project_" + str(self.uuid)

    def get_disk_path(self):
        return "/projects/" + str(self.uuid)

    def _create_geoserver_proj_workspace(self):
        requests.post("http://localhost/geoserver/geoserver/rest/workspaces",
                      headers={"Content-Type": "application/json"},
                      data='{"workspace": {"name": "' + self._get_geoserver_ws_name() + '"}}',
                      auth=HTTPBasicAuth('admin', 'geoserver'))

        self._create_mainortho_datastore()
        # For multispectral: repeat for any bands apart from RGB

    def _create_mainortho_datastore(self):
        os.makedirs(self.get_disk_path() + "/mainortho")
        # For multispectral: slice GeoTIFF bands 0:2, save on /projects/uuid/mainortho
        # Otherwise: just copy GeoTIFFs to /projects/uuid/mainortho
        for flight in self.flights.all():
            # Copy all TIFFs to project folder, rename them
            shutil.copy(flight.get_disk_path() + "/odm_orthophoto/odm_orthophoto.tif",
                        self.get_disk_path() + "/mainortho")
            os.rename(self.get_disk_path() + "/mainortho/odm_orthophoto.tif",
                      self.get_disk_path() + "/mainortho/" + "ortho_{:04d}{:02d}{:02d}.tif".format(flight.date.year,
                                                                                                   flight.date.month,
                                                                                                   flight.date.day))
        with open(self.get_disk_path() + "/mainortho/indexer.properties", "w") as f:
            f.write("""TimeAttribute=ingestion
Schema=*the_geom:Polygon,location:String,ingestion:java.util.Date
PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion)""")
        with open(self.get_disk_path() + "/mainortho/timeregex.properties", "w") as f:
            f.write("regex=[0-9]{8},format=yyyyMMdd")
        # For multispectral: slice multispectral bands, save on /projects/uuid/nir and /projects/uuid/rededge
        # Create datastore and ImageMosaic
        GEOSERVER_BASE_URL = "http://localhost/geoserver/geoserver/rest/workspaces/"
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/mainortho/external.imagemosaic",
            headers={"Content-Type": "text/plain"},
            data="file:///media/USB/" + str(self.uuid) + "/mainortho/",
            auth=HTTPBasicAuth('admin', 'geoserver'))
        # Enable time dimension
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/mainortho/coverages/mainortho.json",
            headers={"Content-Type": "application/json"},
            data='{"coverage": { "enabled": true, "metadata": { "entry": [ { "@key": "time", ' +
                 '"dimensionInfo": { "enabled": true, "presentation": "LIST", "units": "ISO8601", ' +
                 '"defaultValue": "" }} ] } }} ',
            auth=HTTPBasicAuth('admin', 'geoserver'))

    def delete(self, using=None, keep_parents=False):
        querystring = {"recurse": "true"}
        requests.delete("http://localhost/geoserver/geoserver/rest/workspaces/" + self._get_geoserver_ws_name(),
                        params=querystring,
                        auth=HTTPBasicAuth('admin', 'geoserver'))
        shutil.rmtree(self.get_disk_path())

        super(UserProject, self).delete(using, keep_parents)


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
    name = models.CharField(max_length=50)
    date = models.DateField()
    camera = models.CharField(max_length=10, choices=[(tag.name, tag.value) for tag in Camera])
    multispectral_processing = models.BooleanField(default=False)
    annotations = models.TextField()
    deleted = models.BooleanField(default=False)
    state = models.CharField(max_length=10,
                             choices=[(tag.name, tag.value) for tag in FlightState],
                             default=FlightState.WAITING.name)
    processing_time = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'user'], name='unique name on same user')
        ]

    def get_nodeodm_info(self):
        if self.state != FlightState.PROCESSING.name:
            return {}

        data = requests.get("http://localhost:3000/task/" + str(self.uuid) + "/info").json()
        return {"processingTime": data.get("processingTime", 0), "progress": data.get("progress", 0),
                "numImages": data.get("imagesCount", 0)}

    def get_disk_path(self):
        return "/flights/" + str(self.uuid)

    def get_thumbnail_path(self):
        return "./tmp/" + str(self.uuid) + "_thumbnail.png"

    def _get_geoserver_ws_name(self):
        return "flight_" + str(self.uuid)

    def create_geoserver_workspace_and_upload_geotiff(self):
        requests.post("http://localhost/geoserver/geoserver/rest/workspaces",
                      headers={"Content-Type": "application/json"},
                      data='{"workspace": {"name": "' + self._get_geoserver_ws_name() + '"}}',
                      auth=HTTPBasicAuth('admin', 'geoserver'))
        using_micasense = self.camera == Camera.REDEDGE.name
        geotiff_name = "odm_orthophoto.tif" if not using_micasense else "rgb.tif"
        requests.put(
            "http://localhost/geoserver/geoserver/rest/workspaces/" + self._get_geoserver_ws_name() + "/coveragestores/ortho/external.geotiff",
            headers={"Content-Type": "text/plain"},
            data="file:///media/input/" + str(self.uuid) + "/odm_orthophoto/" + geotiff_name,
            auth=HTTPBasicAuth('admin', 'geoserver'))
        if using_micasense:  # Change name to odm_orthomosaic and configure transparent color on black
            requests.put(
                "http://localhost/geoserver/geoserver/rest/workspaces/" + self._get_geoserver_ws_name() + "/coveragestores/ortho/coverages/rgb.json",
                headers={"Content-Type": "application/json"},
                data='{"coverage": {"name": "odm_orthophoto", "title": "odm_orthophoto", "enabled": true, ' +
                     '"parameters": { "entry": [ { "string": [ "InputTransparentColor", "#000000" ] }, ' +
                     '{ "string": [ "SUGGESTED_TILE_SIZE", "512,512" ] } ] }}} ',
                auth=HTTPBasicAuth('admin', 'geoserver'))


def create_nodeodm_task(sender, instance: Flight, created, **kwargs):
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


def link_demo_flight_to_active_users(sender, instance: Flight, created, **kwargs):
    if created and instance.is_demo:
        for user in User.objects.filter(is_active=True).all():
            user.demo_flights.add(instance)


def delete_nodeodm_task(sender, instance: Flight, **kwargs):
    requests.post("http://localhost:3000/task/remove",
                  headers={'Content-Type': "application/x-www-form-urlencoded"},
                  data="uuid=" + str(instance.uuid), )


def delete_geoserver_workspace(sender, instance: Flight, **kwargs):
    querystring = {"recurse": "true"}
    requests.delete("http://localhost/geoserver/geoserver/rest/workspaces/flight_" + str(instance.uuid),
                    params=querystring,
                    auth=HTTPBasicAuth('admin', 'geoserver'))


def delete_thumbnail(sender, instance: Flight, **kwargs):
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
