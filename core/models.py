import json
import logging
import os
import re
import shutil
import subprocess
from typing import Union
import matplotlib.pyplot as plt
import numpy

import pyproj
from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.template.loader import render_to_string
from enum import Enum
import uuid as u

from django.db.models.signals import post_save, post_delete, m2m_changed

import requests
from django.dispatch import receiver
from requests.auth import HTTPBasicAuth
from PIL import Image, ImageOps
from weasyprint import HTML

from core.parser import FormulaParser


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
    demo_projects = models.ManyToManyField('UserProject', related_name='demo_users')


class BaseProject(models.Model):
    uuid = models.UUIDField(primary_key=True, default=u.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField()
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class UserProject(BaseProject):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="user_projects")
    flights = models.ManyToManyField("Flight", related_name="user_projects")
    must_create_workspace = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)

    def _get_geoserver_ws_name(self):
        return "project_" + str(self.uuid)

    def get_disk_path(self):
        return "/projects/" + str(self.uuid)

    def all_flights_multispectral(self):
        return all(flight.camera == Camera.REDEDGE.name for flight in self.flights.all())

    def _create_geoserver_proj_workspace(self):
        requests.post("http://container-nginx/geoserver/geoserver/rest/workspaces",
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
            ortho_name = "rgb.tif" if flight.camera == Camera.REDEDGE.name else "odm_orthophoto.tif"
            shutil.copy(flight.get_disk_path() + "/odm_orthophoto/" + ortho_name,
                        self.get_disk_path() + "/mainortho")
            os.rename(self.get_disk_path() + "/mainortho/" + ortho_name,
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
        GEOSERVER_BASE_URL = "http://container-nginx/geoserver/geoserver/rest/workspaces/"
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
                 '"defaultValue": "" }} ] }, "parameters": { "entry": [ { "string": [ ' +
                 '"OutputTransparentColor", "#000000" ] } ] } }} ',
            auth=HTTPBasicAuth('admin', 'geoserver'))

    def _create_index_datastore(self, index):
        index_folder = self.get_disk_path() + "/" + index
        os.makedirs(index_folder)
        for flight in self.flights.all():
            # Copy all TIFFs to project folder, rename them
            ortho_name = index + ".tif"
            shutil.copy(flight.get_disk_path() + "/odm_orthophoto/" + ortho_name,
                        index_folder)
            os.rename(index_folder + "/" + ortho_name,
                      index_folder + "/" + "ortho_{:04d}{:02d}{:02d}.tif".format(flight.date.year,
                                                                                 flight.date.month,
                                                                                 flight.date.day))
        with open(index_folder + "/indexer.properties", "w") as f:
            f.write("""TimeAttribute=ingestion
        Schema=*the_geom:Polygon,location:String,ingestion:java.util.Date
        PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion)""")
        with open(index_folder + "/timeregex.properties", "w") as f:
            f.write("regex=[0-9]{8},format=yyyyMMdd")

        GEOSERVER_API_ENTRYPOINT = "http://container-nginx/geoserver/geoserver/rest/"
        GEOSERVER_BASE_URL = GEOSERVER_API_ENTRYPOINT + "workspaces/"
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/" + index + "/external.imagemosaic",
            headers={"Content-Type": "text/plain"},
            data="file:///media/USB/" + str(self.uuid) + "/" + index + "/",
            auth=HTTPBasicAuth('admin', 'geoserver'))
        # Enable time dimension
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/" + index + "/coverages/" + index + ".json",
            headers={"Content-Type": "application/json"},
            data='{"coverage": { "enabled": true, "metadata": { "entry": [ { "@key": "time", ' +
                 '"dimensionInfo": { "enabled": true, "presentation": "LIST", "units": "ISO8601", ' +
                 '"defaultValue": "" }} ] }, "parameters": { "entry": [ { "string": [ ' +
                 '"OutputTransparentColor", "#000000" ] } ] } }} ',
            auth=HTTPBasicAuth('admin', 'geoserver'))
        # Enable gradient (is on a different URL because... reasons???)
        requests.put(
            GEOSERVER_API_ENTRYPOINT + "layers/" + self._get_geoserver_ws_name() + ":" + index + ".json",
            headers={"Content-Type": "application/json"},
            data='{"layer": {"defaultStyle": {"name": "gradient"}}}',
            auth=HTTPBasicAuth('admin', 'geoserver'))


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

        data = requests.get("http://container-nodeodm:3000/task/" + str(self.uuid) + "/info").json()
        return {"processingTime": data.get("processingTime", 0), "progress": data.get("progress", 0),
                "numImages": data.get("imagesCount", 0)}

    def get_disk_path(self):
        return "/flights/" + str(self.uuid)

    def get_thumbnail_path(self):
        return "./tmp/" + str(self.uuid) + "_thumbnail.png"

    def get_png_ortho_path(self):
        return self.get_disk_path() + "/odm_orthophoto/odm_orthophoto.png"

    def get_dsm_path(self, extension="png"):
        return self.get_disk_path() + "/odm_dem/dsm_colored_hillshade.{}".format(extension)

    def get_annotated_png_ortho_path(self):
        return self.get_disk_path() + "/odm_orthophoto/odm_orthophoto_annotated.png"

    def _get_geoserver_ws_name(self):
        return "flight_" + str(self.uuid)

    def _try_create_image_from_ortho(self, out_path, thumbnail):
        if self.state != FlightState.COMPLETE.name:
            return
        if self.camera == Camera.REDEDGE.name:
            original_dir = os.getcwd()
            os.chdir(self.get_disk_path() + "/odm_orthophoto/")
            os.system(
                'gdal_translate -b 3 -b 2 -b 1 -mask "6" odm_orthophoto.tif rgb.tif -scale 0 65535 -ot Byte -co "TILED=YES"')
            os.chdir(original_dir)

            source_image = "rgb.tif"
            mask = source_image + ".msk"
        else:
            source_image = "odm_orthophoto.tif"
            mask = None

        size = (512, 512)

        infile = self.get_disk_path() + "/odm_orthophoto/" + source_image
        try:
            im = Image.open(infile)
            if thumbnail:
                im.thumbnail(size)
                im = ImageOps.fit(im, size)
            if mask:
                msk = Image.open(self.get_disk_path() + "/odm_orthophoto/" + mask).split()[0]
                if thumbnail:
                    msk.thumbnail(size)
                    msk = ImageOps.fit(msk, size)
                im.putalpha(msk)

            im.save(out_path, "PNG")
        except IOError as e:
            print(e)

    def _try_tiff_to_png(self, tiff, png):
        try:
            im = Image.open(tiff)
            im.save(png, "PNG")
        except IOError as e:
            print(e)

    def try_create_thumbnail(self):
        self._try_create_image_from_ortho(self.get_thumbnail_path(), True)

    def try_create_png_ortho(self):
        self._try_create_image_from_ortho(self.get_png_ortho_path(), False)

    def try_create_png_dsm(self):
        self._try_tiff_to_png(self.get_dsm_path("tif"), self.get_dsm_path("png"))

    def try_create_annotated_png_ortho(self):
        # from core.models import *; Flight.objects.first().try_create_annotated_png_ortho()
        result = subprocess.run(['gdalinfo', '-proj4', 'odm_orthophoto.tif'], stdout=subprocess.PIPE,
                                cwd=self.get_disk_path() + "/odm_orthophoto").stdout.decode("utf-8")
        local_proj = re.search(r"PROJ\.4 string is:[\r\n]+'([^\r\n']+)'", result).groups()[0]
        offs_x, offs_y = re.search(r"Origin = \((-?\d+\.\d+),(-?\d+\.\d+)\)", result).groups()
        ps_x, ps_y = re.search(r"Pixel Size = \((-?\d+\.\d+),(-?\d+\.\d+)\)", result).groups()
        transformer = pyproj.Transformer.from_crs("epsg:4326", local_proj)
        with open(self.get_disk_path() + "/images.json") as f:
            images = json.loads(f.read())
        image_coords = {}
        for image in images:
            coord_x, coord_y = transformer.transform(image["latitude"], image["longitude"])
            pixel_x = int((coord_x - float(offs_x)) / float(ps_x))
            pixel_y = int((coord_y - float(offs_y)) / float(ps_y))
            image_coords[image["filename"]] = (pixel_x, pixel_y)
        im = plt.imread(self.get_png_ortho_path())
        fig = plt.figure()
        plt.axis('off')
        implot = plt.imshow(im, zorder=1)
        for image_name, (x, y) in image_coords.items():
            plt.scatter(x, y, zorder=2, color="r")
            # Uncomment below to show arrows on images
            # plt.arrow(x, y, 300, 300, color="r", head_length=100,head_width=80, zorder=2)

        def fig2data(fig):
            """
            @brief Convert a Matplotlib figure to a 4D numpy array with RGBA channels and return it
            @param fig a matplotlib figure
            @return a numpy 3D array of RGBA values
            """
            # draw the renderer
            fig.canvas.draw()

            # Get the RGBA buffer from the figure
            data = numpy.fromstring(fig.canvas.tostring_rgb(), dtype=numpy.uint8, sep='')
            return data.reshape(fig.canvas.get_width_height()[::-1] + (3,))

        plt.imsave(self.get_disk_path() + "/odm_orthophoto/odm_orthophoto_annotated.png", fig2data(fig))

    def create_index_raster(self, index: str, formula: str):
        COMMANDS = {
            "ndvi": 'gdal_calc.py -A odm_orthophoto.tif --A_band=3 -B odm_orthophoto.tif --B_band=4 --calc="((asarray(B,dtype=float32)-asarray(A, dtype=float32))/(asarray(B, dtype=float32)+asarray(A, dtype=float32)) + 1.) * 127." --outfile=ndvi.tif --type=Byte --co="TILED=YES" --overwrite --NoDataValue=-1',
            "ndre": 'gdal_calc.py -A odm_orthophoto.tif --A_band=5 -B odm_orthophoto.tif --B_band=4 --calc="((asarray(B,dtype=float32)-asarray(A, dtype=float32))/(asarray(B, dtype=float32)+asarray(A, dtype=float32)) + 1.) * 127." --outfile=ndre.tif --type=Byte --co="TILED=YES" --overwrite --NoDataValue=-1'}
        if self.state != FlightState.COMPLETE.name or self.camera != Camera.REDEDGE.name:
            return
        original_dir = os.getcwd()
        os.chdir(self.get_disk_path() + "/odm_orthophoto/")
        # NDVI and NDRE are built-in, anything else gets parsed
        command = COMMANDS.get(index, None) or FormulaParser().generate_gdal_calc_command(formula, index)
        os.system(command)  # Create raster, save it to <index>.tif on folder <flight_uuid>/odm_orthophoto
        os.chdir(original_dir)

    def create_geoserver_workspace_and_upload_geotiff(self):
        requests.post("http://container-nginx/geoserver/geoserver/rest/workspaces",
                      headers={"Content-Type": "application/json"},
                      data='{"workspace": {"name": "' + self._get_geoserver_ws_name() + '"}}',
                      auth=HTTPBasicAuth('admin', 'geoserver'))
        using_micasense = self.camera == Camera.REDEDGE.name
        geotiff_name = "odm_orthophoto.tif" if not using_micasense else "rgb.tif"
        requests.put(
            "http://container-nginx/geoserver/geoserver/rest/workspaces/" + self._get_geoserver_ws_name() + "/coveragestores/ortho/external.geotiff",
            headers={"Content-Type": "text/plain"},
            data="file:///media/input/" + str(self.uuid) + "/odm_orthophoto/" + geotiff_name,
            auth=HTTPBasicAuth('admin', 'geoserver'))
        if using_micasense:  # Change name to odm_orthomosaic and configure transparent color on black
            requests.put(
                "http://container-nginx/geoserver/geoserver/rest/workspaces/" + self._get_geoserver_ws_name() + "/coveragestores/ortho/coverages/rgb.json",
                headers={"Content-Type": "application/json"},
                data='{"coverage": {"name": "odm_orthophoto", "title": "odm_orthophoto", "enabled": true, ' +
                     '"parameters": { "entry": [ { "string": [ "InputTransparentColor", "#000000" ] }, ' +
                     '{ "string": [ "SUGGESTED_TILE_SIZE", "512,512" ] } ] }}} ',
                auth=HTTPBasicAuth('admin', 'geoserver'))

    def create_report(self, context):
        report = render_to_string('reports/report.html', {"flight": self, "extras": context})
        pdfpath = self.get_disk_path() + "/report.pdf"
        HTML(string=report).write_pdf(pdfpath)
        return pdfpath

    def create_report_movil(self, context):
        report = render_to_string('reports/report.html', {"flight": self, "extras": context})
        pdfpath = self.get_disk_path() + "/report.pdf"
        HTML(string=report).write_pdf(pdfpath)
        return pdfpath

    def make_demo(self):
        if self.state != FlightState.COMPLETE.name:
            return False
        self.is_demo = True
        self.user = None
        for user in User.objects.all():
            user.demo_flights.add(self)
        self.save()
        return True


def create_nodeodm_task(sender, instance: Flight, created, **kwargs):
    if created:
        requests.post('http://container-nodeodm:3000/task/new/init',
                      headers={"set-uuid": str(instance.uuid)},
                      files={
                          "name": (None, instance.name),
                          "webhook": (None, "http://container-nginx/api/webhook-processing-complete"),
                          "options": (
                              None, json.dumps([{"name": "dsm", "value": True}, {"name": "time", "value": True}])
                          )
                      })


def delete_nodeodm_task(sender, instance: Flight, **kwargs):
    requests.post("http://container-nodeodm:3000/task/remove",
                  headers={'Content-Type': "application/x-www-form-urlencoded"},
                  data="uuid=" + str(instance.uuid), )


def delete_geoserver_workspace(sender, instance: Union[Flight, UserProject], **kwargs):
    querystring = {"recurse": "true"}
    requests.delete("http://container-nginx/geoserver/geoserver/rest/workspaces/" + instance._get_geoserver_ws_name(),
                    params=querystring,
                    auth=HTTPBasicAuth('admin', 'geoserver'))


def delete_on_disk(sender, instance: UserProject, **kwargs):
    shutil.rmtree(instance.get_disk_path())


def delete_thumbnail(sender, instance: Flight, **kwargs):
    if os.path.exists(instance.get_thumbnail_path()):
        os.remove(instance.get_thumbnail_path())


post_save.connect(create_nodeodm_task, sender=Flight)
post_delete.connect(delete_nodeodm_task, sender=Flight)
post_delete.connect(delete_thumbnail, sender=Flight)
post_delete.connect(delete_geoserver_workspace, sender=Flight)
post_delete.connect(delete_geoserver_workspace, sender=UserProject)
post_delete.connect(delete_on_disk, sender=UserProject)


class ArtifactType(Enum):
    ORTHOMOSAIC = "Orthomosaic"
    SHAPEFILE = "Shapefile"
    INDEX = "Index"

    @classmethod
    def filename(cls, art):
        if art.type == ArtifactType.SHAPEFILE.name:
            return "poly.shp"
        elif art.type == ArtifactType.INDEX.name:
            return art.name + ".tif"


class Artifact(models.Model):
    type = models.CharField(max_length=20, choices=[(tag.name, tag.value) for tag in ArtifactType])
    name = models.CharField(max_length=256)
    title = models.CharField(max_length=256)
    project = models.ForeignKey(UserProject, on_delete=models.CASCADE, related_name="artifacts", null=True)

    def get_disk_path(self):
        return self.project.get_disk_path() + "/" + self.name + "/" + ArtifactType.filename(self)


class BlockType(Enum):
    USER_NAME = "UserName"
    IP = "Ip"
    EMAIL = "Email"
    DOMAIN = "Domain"


class BlockCriteria(models.Model):
    type = models.CharField(max_length=20, choices=[(tag.name, tag.value) for tag in BlockType])
    ip = models.GenericIPAddressField(max_length=256, null=True)
    value = models.CharField(max_length=80, null=True)
