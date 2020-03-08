# ViewSets define the view behavior.
import json
import os
import sys

from PIL import Image, ImageOps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated

from core.models import *
from core.permissions import OnlySelfUnlessAdminPermission
from core.serializers import *

import requests
from requests.auth import HTTPBasicAuth


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, OnlySelfUnlessAdminPermission,)
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.all() if self.request.user.is_staff else User.objects.filter(pk=self.request.user.pk)


class FlightViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = FlightSerializer

    def get_queryset(self):
        return Flight.objects.filter(user=self.request.user) | self.request.user.demo_flights.all()

    def perform_create(self, serializer):
        if not self.request.user.is_staff or "target_user" not in self.request.POST:
            serializer.save(user=self.request.user)
        else:
            serializer.save(user=User.objects.get(pk=self.request.POST["target_user"]))

    def perform_destroy(self, instance):
        if self.request.user.is_staff or instance.user == self.request.user:
            instance.delete()
        else:  # User is not admin nor file owner
            if instance.is_demo:
                self.request.user.demo_flights.remove(instance)  # Remove demo flight ONLY FOR USER!


class ArtifactViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = ArtifactSerializer

    def get_queryset(self):
        return Artifact.objects.all()


class UserProjectViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserProjectSerializer

    def get_queryset(self):
        return UserProject.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_staff or "target_user" not in self.request.POST:
            serializer.save(user=self.request.user)
        else:
            serializer.save(user=User.objects.get(pk=self.request.POST["target_user"]))


@csrf_exempt
def upload_images(request, uuid):
    flight = get_object_or_404(Flight, uuid=uuid)
    user = Token.objects.get(key=request.headers["Authorization"][6:]).user
    if not user.is_staff and not flight.user == user:
        return HttpResponse(status=403)

    files = []
    filenames = []
    for f in request.FILES.getlist("images"):  # save temp files to disk before uploading
        path = default_storage.save('tmp/' + f.name, ContentFile(f.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        filenames.append(tmp_file)
        files.append(('images', open(tmp_file, "rb")))
    # upload files to NodeODM server
    r = requests.post("http://localhost:3000/task/new/upload/" + str(flight.uuid), files=files)
    if r.status_code != 200:
        return HttpResponse(status=500)
    for f in filenames:  # delete temp files from disk
        os.remove(f)

    # start processing Flight on NodeODM
    r = requests.post("http://localhost:3000/task/new/commit/" + str(flight.uuid))
    if r.status_code != 200:
        return HttpResponse(status=500)

    flight.state = FlightState.PROCESSING.name
    flight.save()  # change Flight state to PROCESSING

    return HttpResponse()


def _try_create_thumbnail(flight):
    if flight.camera == Camera.REDEDGE.name:
        original_dir = os.getcwd()
        os.chdir(flight.get_disk_path() + "/odm_orthophoto/")
        os.system(
            'gdal_translate -b 3 -b 2 -b 1 -mask "6" odm_orthophoto.tif rgb.tif -scale 0 65535 -ot Byte -co "TILED=YES"')
        os.chdir(original_dir)

        source_image = "rgb.tif"
        mask = source_image + ".msk"
    else:
        source_image = "odm_orthophoto.tif"
        mask = None
    print("THUMBNAIL: ", source_image, mask)

    size = (512, 512)

    infile = flight.get_disk_path() + "/odm_orthophoto/" + source_image
    try:
        im = Image.open(infile)
        im.thumbnail(size)
        im = ImageOps.fit(im, size)
        if mask:
            msk = Image.open(flight.get_disk_path() + "/odm_orthophoto/" + mask).split()[0]
            msk.thumbnail(size)
            msk = ImageOps.fit(msk, size)
            im.putalpha(msk)

        im.save(flight.get_thumbnail_path(), "PNG")
    except IOError as e:
        print(e)


@csrf_exempt
def webhook_processing_complete(request):
    data = json.loads(request.body.decode("utf-8"))
    flight = Flight.objects.get(uuid=data["uuid"])

    if data["status"]["code"] == 30:
        flight.state = FlightState.ERROR.name
    elif data["status"]["code"] == 40:
        flight.state = FlightState.COMPLETE.name
    elif data["status"]["code"] == 50:
        flight.state = FlightState.CANCELED.name
    flight.processing_time = data.get("processingTime", 0)
    flight.save()

    _try_create_thumbnail(flight)
    flight.create_geoserver_workspace_and_upload_geotiff()  # _try_create_thumbnail must have been invoked here!

    return HttpResponse()


def download_artifact(request, uuid, artifact):
    # flight = get_object_or_404(Flight, uuid=uuid)
    # user = Token.objects.get(key=request.headers["Authorization"][6:]).user
    # if not user.is_staff and not flight.user == user:
    #     return HttpResponse(status=403)

    print(artifact)
    filepath = "/flights/" + str(uuid)
    if artifact == "orthomosaic.png":
        filepath += "/odm_orthophoto/odm_orthophoto.png"
    elif artifact == "orthomosaic.tiff":
        filepath += "/odm_orthophoto/odm_orthophoto.tif"
    elif artifact == "3dmodel":
        filepath += "/odm_meshing/odm_mesh.ply"
    elif artifact == "3dmodel_texture":
        filepath += "/odm_texturing/odm_textured_model.obj"
    elif artifact == "thumbnail":
        filepath = "./tmp/" + str(uuid) + "_thumbnail.png"
    else:
        raise Http404
    return serve(request, os.path.basename(filepath), os.path.dirname(filepath))


@csrf_exempt
def upload_shapefile(request, uuid):
    from django.core.files.uploadedfile import UploadedFile

    project = UserProject.objects.get(pk=uuid)
    file: UploadedFile = request.FILES["shapefile"]
    shp_name = ".".join(file.name.split(".")[:-1])
    project.artifacts.create(name=shp_name, type=ArtifactType.SHAPEFILE.name, title=request.POST["title"])

    # Write file to disk on project folder
    os.makedirs(project.get_disk_path() + "/" + shp_name)
    with open(project.get_disk_path() + "/" + shp_name + "/" + file.name, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)

    GEOSERVER_BASE_URL = "http://localhost/geoserver/geoserver/rest/workspaces/"

    requests.put(
        GEOSERVER_BASE_URL + project._get_geoserver_ws_name() + "/datastores/" + shp_name + "/"
                                                                                            "external.shp",
        headers={"Content-Type": "text/plain"},
        data="file:///media/USB/" + str(project.uuid) + "/" + shp_name + "/" + file.name,
        auth=HTTPBasicAuth('admin', 'geoserver'))

    r = requests.put(
        GEOSERVER_BASE_URL + project._get_geoserver_ws_name() + "/datastores/" + shp_name + "/featuretypes/" + shp_name + ".json",
        headers={"Content-Type": "application/json"},
        data='{"featureType": {"enabled": true, "srs": "EPSG:4326" }}',
        auth=HTTPBasicAuth('admin', 'geoserver'))
    print(r.status_code, r.text)
    return HttpResponse(status=201)


def preview_flight_url(request, uuid):
    flight = get_object_or_404(Flight, uuid=uuid)
    # user = Token.objects.get(key=request.headers["Authorization"][6:]).user
    # if not user.is_staff and not flight.user == user:
    #     return HttpResponse(status=403)

    ans = requests.get(
        "http://localhost/geoserver/geoserver/rest/workspaces/" + flight._get_geoserver_ws_name() +
        "/coveragestores/ortho/coverages/odm_orthophoto.json",
        auth=HTTPBasicAuth('admin', 'geoserver')).json()
    bbox = ans["coverage"]["nativeBoundingBox"]
    base = "/geoserver/geoserver/" + flight._get_geoserver_ws_name() + \
           "/wms?service=WMS&version=1.1.0&request=GetMap&layers=" + flight._get_geoserver_ws_name() + \
           ":odm_orthophoto&styles=&bbox=" + \
           ','.join(map(str, (bbox["minx"], bbox["miny"], bbox["maxx"], bbox["maxy"]))) + \
           "&width=1000&height=1000&srs=EPSG:32617&format=application/openlayers"

    return JsonResponse({"url": base, "bbox": bbox, "srs": ans["coverage"]["srs"]})


def mapper(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    return render(request, "geoext/examples/tree/panel.html",
                  {"project_name": project.name,
                   "project_notes": project.description,
                   "project_geoserver_path": project._get_geoserver_ws_name(),
                   "upload_shapefiles_path": "/#/projects/" + str(project.uuid) + "/upload/shapefile",
                   "uuid": project.uuid,
                   "flights": project.flights.all().order_by("date")})


def mapper_bbox(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    ans = requests.get(
        "http://localhost/geoserver/geoserver/rest/workspaces/" + project._get_geoserver_ws_name() +
        "/coveragestores/mainortho/coverages/mainortho.json",
        auth=HTTPBasicAuth('admin', 'geoserver')).json()

    return JsonResponse({"bbox": ans["coverage"]["nativeBoundingBox"], "srs": ans["coverage"]["srs"]})


def mapper_shapefiles(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    return JsonResponse({"shapefiles": [
        {"name": art.title, "layer": project._get_geoserver_ws_name() + ":" + art.name}
        for art in project.artifacts.all()
        if art.type == ArtifactType.SHAPEFILE.name
    ]})


def mapper_paneljs(request):
    filepath = "./templates/geoext/examples/tree/panel.js"
    return serve(request, os.path.basename(filepath), os.path.dirname(filepath))


def mapper_ol(request, path):
    filepath = "./templates/geoext/examples/lib/ol/" + path
    return serve(request, os.path.basename(filepath), os.path.dirname(filepath))


def mapper_src(request, path):
    filepath = "./templates/geoext/src/" + path
    return serve(request, os.path.basename(filepath), os.path.dirname(filepath))
