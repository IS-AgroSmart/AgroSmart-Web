# ViewSets define the view behavior.
import json
import os
import re
import sys

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from lark.exceptions import LarkError
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated

from core.models import *
from core.parser import FormulaParser
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

    flight.try_create_thumbnail()
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
    # shapefile is an array with files [X.shp, X.shx, X.dbf], in some order
    file: UploadedFile = request.FILES.getlist("shapefile")[0]  # gets name X.Y (cannot guarantee Y)
    shp_name = ".".join(file.name.split(".")[:-1])  # remove extension to get only X
    project.artifacts.create(name=shp_name, type=ArtifactType.SHAPEFILE.name, title=request.POST["title"])

    # Write file(s) to disk on project folder
    os.makedirs(project.get_disk_path() + "/" + shp_name)
    for file in request.FILES.getlist("shapefile"):
        extension = file.name.split(".")[-1]
        with open(project.get_disk_path() + "/" + shp_name + "/" + shp_name + "." + extension, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

    GEOSERVER_BASE_URL = "http://localhost/geoserver/geoserver/rest/workspaces/"

    requests.put(
        GEOSERVER_BASE_URL + project._get_geoserver_ws_name() + "/datastores/" + shp_name + "/"
                                                                                            "external.shp",
        headers={"Content-Type": "text/plain"},
        data="file:///media/USB/" + str(project.uuid) + "/" + shp_name + "/" + shp_name + ".shp",
        auth=HTTPBasicAuth('admin', 'geoserver'))

    requests.put(
        GEOSERVER_BASE_URL + project._get_geoserver_ws_name() + "/datastores/" + shp_name + "/featuretypes/" + shp_name + ".json",
        headers={"Content-Type": "application/json"},
        data='{"featureType": {"enabled": true, "srs": "EPSG:4326" }}',
        auth=HTTPBasicAuth('admin', 'geoserver'))
    return HttpResponse(status=201)


@csrf_exempt
def upload_geotiff(request, uuid):
    from django.core.files.uploadedfile import UploadedFile

    project = UserProject.objects.get(pk=uuid)
    file: UploadedFile = request.FILES.get("geotiff")  # file is called X.tiff
    geotiff_name = ".".join(file.name.split(".")[:-1])  # Remove extension, get X
    project.artifacts.create(name=geotiff_name, type=ArtifactType.ORTHOMOSAIC.name, title=request.POST["title"])

    # Write file to disk on project folder
    os.makedirs(project.get_disk_path() + "/" + geotiff_name)
    with open(project.get_disk_path() + "/" + geotiff_name + "/" + geotiff_name + ".tiff", "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)

    GEOSERVER_BASE_URL = "http://localhost/geoserver/geoserver/rest/workspaces/"

    requests.put(
        GEOSERVER_BASE_URL + project._get_geoserver_ws_name() + "/coveragestores/" + geotiff_name + "/"
                                                                                                    "external.geotiff",
        headers={"Content-Type": "text/plain"},
        data="file:///media/USB/" + str(project.uuid) + "/" + geotiff_name + "/" + geotiff_name + ".tiff",
        auth=HTTPBasicAuth('admin', 'geoserver'))

    requests.put(
        GEOSERVER_BASE_URL + project._get_geoserver_ws_name() + "/coveragestores/" + geotiff_name + "/coverages/" + geotiff_name + ".json",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"coverage": {
            "enabled": True,
            "parameters": {"entry": [
                {"string": ["InputTransparentColor", "#000000"]},
                {"string": ["SUGGESTED_TILE_SIZE", "512,512"]}
            ]}
        }}),
        auth=HTTPBasicAuth('admin', 'geoserver'))
    return HttpResponse(status=201)


def upload_shapefile(request, uuid):
    project = UserProject.objects.get(pk=uuid)
    # Add Artifact record to Project
    # Save file on project.get_disk_path() + "/" + filename
    # Rename file to poly.shp

    # PUT request to {{url}}/workspaces/project_{{uuid}}/datastores/{{filename}}/featuretypes/poly.json
    # Content-Type = text/plain
    # Body = file:///media/USB/{{uuid}}/{{filename}}/poly.shp

    # PUT to {{url}}/workspaces/project_{{uuid}}/datastores/{{filename}}/featuretypes/poly.json
    # Content-Type = application/json
    # Body = {"featureType": {
    # 	"enabled": true,
    # 	"srs": "EPSG:4326"
    # }}
    return HttpResponse


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


def check_formula(request):
    return HttpResponse(status=200 if FormulaParser().is_valid(request.GET["formula"]) else 400)


@csrf_exempt
def create_raster_index(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    if not project.all_flights_multispectral():
        return HttpResponse("Not all flights are multispectral!", status=400)

    data = json.loads(request.body.decode('utf-8'))
    print(data)

    index = data.get("index", "custom")
    clean_index = re.sub(r"[^a-z0-9_-]", "", index)
    formula = data.get("formula", "")

    print("FORMULA->" + formula)
    for flight in project.flights.all():
        flight.create_index_raster(clean_index, formula)
    project._create_index_datastore(clean_index)
    project.artifacts.create(name=clean_index, type=ArtifactType.INDEX.name, title=clean_index.upper())
    return HttpResponse(status=200)


def mapper(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    return render(request, "geoext/examples/tree/panel.html",
                  {"project_name": project.name,
                   "project_notes": project.description,
                   "project_geoserver_path": project._get_geoserver_ws_name(),
                   "upload_shapefiles_path": "/#/projects/" + str(project.uuid) + "/upload/shapefile",
                   "upload_geotiff_path": "/#/projects/" + str(project.uuid) + "/upload/geotiff",
                   "upload_new_index_path": "/#/projects/" + str(project.uuid) + "/upload/index",
                   "is_multispectral": project.all_flights_multispectral(),
                   "uuid": project.uuid,
                   "flights": project.flights.all().order_by("date")})


def mapper_bbox(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    ans = requests.get(
        "http://localhost/geoserver/geoserver/rest/workspaces/" + project._get_geoserver_ws_name() +
        "/coveragestores/mainortho/coverages/mainortho.json",
        auth=HTTPBasicAuth('admin', 'geoserver')).json()

    return JsonResponse({"bbox": ans["coverage"]["nativeBoundingBox"], "srs": ans["coverage"]["srs"]})


def mapper_artifacts(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    return JsonResponse({"artifacts": [
        {"name": art.title,
         "layer": project._get_geoserver_ws_name() + ":" + art.name,
         "type": art.type}
        for art in project.artifacts.all()
    ]})


def mapper_indices(request, uuid):
    project = UserProject.objects.get(uuid=uuid)

    return JsonResponse({"indices": [
        {"name": art.name, "title": art.title, "layer": project._get_geoserver_ws_name() + ":" + art.name}
        for art in project.artifacts.all()
        if art.type == ArtifactType.INDEX.name
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
