import json
import os
import re
import shutil
import subprocess
from typing import Union
from zipfile import ZipFile

import matplotlib.pyplot as plt
import numpy

import pyproj
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.template.loader import render_to_string
from enum import Enum
import uuid as u

from django.db.models.signals import post_save, post_delete

import requests
from requests.auth import HTTPBasicAuth
from PIL import Image, ImageOps
from weasyprint import HTML

from django.conf import settings
from core.parser import FormulaParser
from core.utils.disk_space_tracking import DiskSpaceTrackerMixin, DiskRelationTrackerMixin
from core.utils.working_dir import cd


class UserType(Enum):
    DEMO_USER = "DemoUser"
    ACTIVE = "Active"
    DELETED = "Deleted"
    ADMIN = "Admin"


class User(DiskRelationTrackerMixin, AbstractUser):
    organization = models.CharField(max_length=20, blank=True)
    type = models.CharField(max_length=20,
                            choices=[(tag.name, tag.value) for tag in UserType],
                            default=UserType.DEMO_USER.name)
    demo_flights = models.ManyToManyField('Flight', related_name='demo_users')
    demo_projects = models.ManyToManyField('UserProject', related_name='demo_users')

    used_space = models.PositiveIntegerField(default=0)
    maximum_space = models.PositiveIntegerField(default=45 * 1024 * 1024)
    remaining_images = models.PositiveIntegerField(default=0)
    image_month_quota = models.PositiveIntegerField(default=3000)

    def get_disk_related_models(self):
        return list(self.flight_set.filter(is_demo=False)) + list(self.user_projects.filter(is_demo=False))


class BaseProject(models.Model):
    uuid = models.UUIDField(primary_key=True, default=u.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField()
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class UserProject(DiskSpaceTrackerMixin, BaseProject):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="user_projects")
    flights = models.ManyToManyField("Flight", related_name="user_projects")
    must_create_workspace = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)

    used_space = models.PositiveIntegerField(default=0)

    def _get_geoserver_ws_name(self):
        return "project_" + str(self.uuid)

    def get_disk_path(self):
        return "/projects/" + str(self.uuid)

    def all_flights_multispectral(self):
        return all(flight.camera == Camera.REDEDGE.name for flight in self.flights.all())

    def _create_geoserver_proj_workspace(self):
        requests.post("http://container-geoserver:8080/geoserver/rest/workspaces",
                      headers={"Content-Type": "application/json"},
                      data='{"workspace": {"name": "' + self._get_geoserver_ws_name() + '"}}',
                      auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))

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
        GEOSERVER_BASE_URL = "http://container-geoserver:8080/geoserver/rest/workspaces/"
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/mainortho/external.imagemosaic",
            headers={"Content-Type": "text/plain"},
            data="file:///media/USB/" + str(self.uuid) + "/mainortho/",
            auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))
        # Enable time dimension
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/mainortho/coverages/mainortho.json",
            headers={"Content-Type": "application/json"},
            data='{"coverage": { "enabled": true, "metadata": { "entry": [ { "@key": "time", ' +
                 '"dimensionInfo": { "enabled": true, "presentation": "LIST", "units": "ISO8601", ' +
                 '"defaultValue": "" }} ] }, "parameters": { "entry": [ { "string": [ ' +
                 '"OutputTransparentColor", "#000000" ] } ] } }} ',
            auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))

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

        GEOSERVER_API_ENTRYPOINT = "http://container-geoserver:8080/geoserver/rest/"
        GEOSERVER_BASE_URL = GEOSERVER_API_ENTRYPOINT + "workspaces/"
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/" + index + "/external.imagemosaic",
            headers={"Content-Type": "text/plain"},
            data="file:///media/USB/" + str(self.uuid) + "/" + index + "/",
            auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))
        # Enable time dimension
        requests.put(
            GEOSERVER_BASE_URL + self._get_geoserver_ws_name() + "/coveragestores/" + index + "/coverages/" + index + ".json",
            headers={"Content-Type": "application/json"},
            data='{"coverage": { "enabled": true, "metadata": { "entry": [ { "@key": "time", ' +
                 '"dimensionInfo": { "enabled": true, "presentation": "LIST", "units": "ISO8601", ' +
                 '"defaultValue": "" }} ] }, "parameters": { "entry": [ { "string": [ ' +
                 '"OutputTransparentColor", "#000000" ] } ] } }} ',
            auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))
        # Enable gradient (is on a different URL because... reasons???)
        requests.put(
            GEOSERVER_API_ENTRYPOINT + "layers/" + self._get_geoserver_ws_name() + ":" + index + ".json",
            headers={"Content-Type": "application/json"},
            data='{"layer": {"defaultStyle": {"name": "gradient"}}}',
            auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))


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


class Flight(DiskSpaceTrackerMixin, models.Model):
    uuid = models.UUIDField(primary_key=True, default=u.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    is_demo = models.BooleanField(default=False)
    name = models.CharField(max_length=50)
    date = models.DateField()
    camera = models.CharField(max_length=10, choices=[(tag.name, tag.value) for tag in Camera])
    annotations = models.TextField()
    deleted = models.BooleanField(default=False)
    state = models.CharField(max_length=10,
                             choices=[(tag.name, tag.value) for tag in FlightState],
                             default=FlightState.WAITING.name)
    processing_time = models.PositiveIntegerField(default=0)
    num_images = models.PositiveIntegerField(default=0)

    used_space = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'user'], name='unique name on same user')
        ]

    def get_nodeodm_info(self):
        if self.state != FlightState.PROCESSING.name:
            return {}

        data = requests.get(
            f"{settings.NODEODM_SERVER_URL}/task/{str(self.uuid)}/info?token={settings.NODEODM_SERVER_TOKEN}").json()
        return {"processingTime": data.get("processingTime", 0), "progress": data.get("progress", 0),
                "numImages": data.get("imagesCount", 0)}

    def get_disk_path(self):
        return "/flights/" + str(self.uuid)

    def get_thumbnail_path(self):
        return "./tmp/" + str(self.uuid) + "_thumbnail.png"

    def get_small_ortho_path(self, extension="png"):
        return f"{self.get_disk_path()}/odm_orthophoto/odm_orthophoto_small.{extension}"

    def get_png_ortho_path(self):
        return self.get_disk_path() + "/odm_orthophoto/odm_orthophoto.png"

    @property
    def orig_dsm_path(self):
        return self.get_disk_path() + "/odm_dem/dsm.tif"

    def get_dsm_path(self, extension="png", colored=True, hillshade=True):
        return self.get_disk_path() + "/odm_dem/dsm{}{}.{}".format("_colored" if colored else "",
                                                                   "_hillshade" if hillshade else "", extension)

    def get_annotated_png_ortho_path(self):
        return self.get_disk_path() + "/odm_orthophoto/odm_orthophoto_annotated.png"

    def _get_geoserver_ws_name(self):
        return "flight_" + str(self.uuid)

    def download_and_decompress_results(self):
        try:
            os.mkdir(self.get_disk_path())
        except FileExistsError:
            pass  # just ignore it and continue as you were
        zip_url = f"{settings.NODEODM_SERVER_URL}/task/{str(self.uuid)}/download/all.zip?token={settings.NODEODM_SERVER_TOKEN}"
        zip_local_name = f"./tmp/{str(self.uuid)}.zip"
        # https://stackoverflow.com/a/16696317
        with requests.get(zip_url) as r:
            r.raise_for_status()
            with open(zip_local_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        with ZipFile(zip_local_name, 'r') as zip:
            zip.extractall(path=self.get_disk_path())
        os.remove(zip_local_name)

    @staticmethod
    def tiff_to_png(tiff: str, png: str):
        assert tiff.endswith(".tif"), f"Input file {tiff} must be a TIFF file!"
        assert png.endswith(".png"), f"Output file {png} must be a PNG file!"
        assert tiff.startswith("/"), f"Input filename {tiff} must be an absolute path"
        assert png.startswith("/"), f"Output filename {png} must be an absolute path"

        cmd = f"gdal_translate {tiff} {png}"
        os.system(cmd)

    def create_rgb_tiff(self):
        with cd(f"{self.get_disk_path()}/odm_orthophoto/"):

            if self.camera == Camera.RGB.name:
                cmd = f'gdal_translate -b 1 -b 2 -b 3 -b mask odm_orthophoto.tif rgb.tif -scale 0 255 -ot Byte -co "TILED=YES"'
            elif self.camera == Camera.REDEDGE.name:
                cmd = f'gdal_translate -b 3 -b 2 -b 1 -b mask odm_orthophoto.tif rgb.tif -scale 0 65535 -ot Byte -co "TILED=YES"'
            else:
                cmd = ""  # should never happen!
            os.system(cmd)

    def _create_orthomosaic(self, height, out_name):
        cmd = f"gdal_translate -outsize 0 {height} {self.get_disk_path()}/odm_orthophoto/rgb.tif {out_name}"
        os.system(cmd)

    def try_create_thumbnail(self):
        self._create_orthomosaic(512, self.get_thumbnail_path())

    def try_create_png_ortho(self):
        self.tiff_to_png(f"{self.get_disk_path()}/odm_orthophoto/rgb.tif", self.get_png_ortho_path())

    def try_create_png_dsm(self):
        self.tiff_to_png(self.get_dsm_path(extension="tif"), self.get_dsm_path(extension="png"))

    def create_colored_dsm(self):
        cmd1 = 'gdaldem color-relief {} ./core/utils/color_relief.txt "{}" -alpha -co ALPHA=YES'.format(
            self.orig_dsm_path, self.get_dsm_path(extension="tif", hillshade=False))
        os.system(cmd1)
        cmd2 = 'gdaldem hillshade {} {} -z 1.0 -s 1.0 -az 315.0 -alt 45.0'.format(
            self.orig_dsm_path, self.get_dsm_path(extension="tif", colored=False))
        os.system(cmd2)
        cmd3 = 'python3 ./core/utils/hsv_merge.py {} {} {}'.format(
            self.get_dsm_path(extension="tif", colored=True, hillshade=False),
            self.get_dsm_path(extension="tif", colored=False, hillshade=True),
            self.get_dsm_path(extension="tif"),
        )
        os.system(cmd3)

    def try_create_dsm_colorbar(self):
        from core.utils.colorbar_creator import create_colorbar
        result = subprocess.run(['gdalinfo', '-mm', 'dsm.tif'], stdout=subprocess.PIPE,
                                cwd=self.get_disk_path() + "/odm_dem/").stdout.decode("utf-8")
        min_val, max_val = re.search(r"Computed Min/Max=(-?\d+\.\d+),(-?\d+\.\d+)", result).groups()
        min_val = "{:.1f} m".format(float(min_val))
        max_val = "{:.1f} m".format(float(max_val))
        create_colorbar(min_val, max_val, save_path=self.get_disk_path() + "/odm_dem/colorbar.png")

    def try_create_annotated_png_ortho(self):
        self._create_orthomosaic(1080, self.get_small_ortho_path(extension="tif"))
        self.tiff_to_png(self.get_small_ortho_path(extension="tif"), self.get_small_ortho_path(extension="png"))

        result = subprocess.run(
            ['gdalinfo', '-proj4', self.get_small_ortho_path(extension="tif")],
            stdout=subprocess.PIPE).stdout.decode("utf-8")
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
        im = plt.imread(self.get_small_ortho_path(extension="png"))
        fig = plt.figure()
        plt.axis('off')
        plt.imshow(im, zorder=1)
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

        with cd(self.get_disk_path() + "/odm_orthophoto/"):
            # NDVI and NDRE are built-in, anything else gets parsed
            command = COMMANDS.get(index, None) or FormulaParser().generate_gdal_calc_command(formula, index)
            os.system(command)  # Create raster, save it to <index>.tif on folder <flight_uuid>/odm_orthophoto

    def create_geoserver_workspace_and_upload_geotiff(self):
        requests.post("http://container-geoserver:8080/geoserver/rest/workspaces",
                      headers={"Content-Type": "application/json"},
                      data='{"workspace": {"name": "' + self._get_geoserver_ws_name() + '"}}',
                      auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))
        using_micasense = self.camera == Camera.REDEDGE.name
        geotiff_name = "odm_orthophoto.tif" if not using_micasense else "rgb.tif"
        requests.put(
            "http://container-geoserver:8080/geoserver/rest/workspaces/" + self._get_geoserver_ws_name() + "/coveragestores/ortho/external.geotiff",
            headers={"Content-Type": "text/plain"},
            data="file:///media/input/" + str(self.uuid) + "/odm_orthophoto/" + geotiff_name,
            auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))
        if using_micasense:  # Change name to odm_orthomosaic and configure transparent color on black
            requests.put(
                "http://container-geoserver:8080/geoserver/rest/workspaces/" + self._get_geoserver_ws_name() + "/coveragestores/ortho/coverages/rgb.json",
                headers={"Content-Type": "application/json"},
                data='{"coverage": {"name": "odm_orthophoto", "title": "odm_orthophoto", "enabled": true, ' +
                     '"parameters": { "entry": [ { "string": [ "InputTransparentColor", "#000000" ] }, ' +
                     '{ "string": [ "SUGGESTED_TILE_SIZE", "512,512" ] } ] }}} ',
                auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))

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

    def unmake_demo(self, user):
        if self.state != FlightState.COMPLETE.name:
            return False
        self.is_demo = False
        self.user = user
        self.demo_users.clear()
        self.save()
        return True


def create_nodeodm_task(sender, instance: Flight, created, **kwargs):
    if created:
        requests.post(f'{settings.NODEODM_SERVER_URL}/task/new/init?token={settings.NODEODM_SERVER_TOKEN}',
                      headers={"set-uuid": str(instance.uuid)},
                      files={
                          "name": (None, instance.name),
                          # "webhook": (None, "http://container-django:8000/api/webhook-processing-complete"),
                          "options": (
                              None, json.dumps([{"name": "dsm", "value": True}, {"name": "dtm", "value": True},
                                                {"name": "time", "value": True}])
                          )
                      })
        requests.post(f'http://container-webhook-adapter:8080/register/{str(instance.uuid)}')


def delete_nodeodm_task(sender, instance: Flight, **kwargs):
    requests.post(f"{settings.NODEODM_SERVER_URL}/task/remove?token={settings.NODEODM_SERVER_TOKEN}",
                  headers={'Content-Type': "application/x-www-form-urlencoded"},
                  data="uuid=" + str(instance.uuid), )


def delete_geoserver_workspace(sender, instance: Union[Flight, UserProject], **kwargs):
    querystring = {"recurse": "true"}
    requests.delete("http://container-geoserver:8080/geoserver/rest/workspaces/" + instance._get_geoserver_ws_name(),
                    params=querystring,
                    auth=HTTPBasicAuth('admin', settings.GEOSERVER_PASSWORD))


def delete_on_disk(sender, instance: Union[Flight, UserProject], **kwargs):
    try:
        shutil.rmtree(instance.get_disk_path())
    except FileNotFoundError:
        pass  # no need to do anything, carry on
    instance.user.update_disk_space()


def delete_thumbnail(sender, instance: Flight, **kwargs):
    if os.path.exists(instance.get_thumbnail_path()):
        os.remove(instance.get_thumbnail_path())


post_save.connect(create_nodeodm_task, sender=Flight)
post_delete.connect(delete_nodeodm_task, sender=Flight)
post_delete.connect(delete_thumbnail, sender=Flight)
post_delete.connect(delete_geoserver_workspace, sender=Flight)
post_delete.connect(delete_geoserver_workspace, sender=UserProject)
post_delete.connect(delete_on_disk, sender=Flight)
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
