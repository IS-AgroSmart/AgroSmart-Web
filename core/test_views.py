import inspect
import io
import json
import os
from datetime import datetime

import pytest
from PIL import Image, ImageOps
from django.contrib.auth import get_user_model
from django.urls import reverse
from httpretty import httpretty
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from core.models import FlightState, UserType, Flight, Camera

pytestmark = pytest.mark.django_db


@pytest.fixture
def users():
    User = get_user_model()
    u1 = User.objects.create_user(username="u1", email="u1@example.com", password="u1")
    u2 = User.objects.create_user(username="u2", email="u2@example.com", password="u2")
    admin = User.objects.create_user(username="admin", email="admin@example.com", password="admin",
                                     type=UserType.ADMIN.name)

    Token.objects.create(user=u1)
    Token.objects.create(user=u2)
    Token.objects.create(user=admin)
    return u1, u2, admin


@pytest.fixture
def flights(users):
    httpretty.enable()
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/init", body="")
    f1 = users[0].flight_set.create(name="flight1", date=datetime.now())
    f1.camera = Camera.REDEDGE.name
    f1.save()
    return f1,


@pytest.fixture
def c():
    return APIClient()


def _auth(c, user):
    token = Token.objects.get(user=user)
    c.credentials(HTTP_AUTHORIZATION='Token ' + token.key)


@pytest.mark.xfail(reason="pyfakefs limitation on /tmp dir")
def test_upload_images_succesful(c, users, flights, fs):
    _auth(c, users[0])
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid), "")
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/commit/" + str(flights[0].uuid), "")
    import django, pytz
    fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
    fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
    fs.create_file("/tmp/image1.jpg", contents="foobar")
    with open("/tmp/image1.jpg") as f:
        resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}), {"images": f})
        assert resp.status_code == 200


def test_upload_images_error_on_creation(c, users, flights, fs):
    import inspect
    import django, pytz

    _auth(c, users[0])
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid), "",
                           status=500)
    fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
    fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
    resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 500


def test_upload_images_error_on_commit(c, users, flights, fs):
    import inspect
    import django, pytz

    _auth(c, users[0])
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid), "")
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/commit/" + str(flights[0].uuid), "",
                           status=500)
    fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
    fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
    resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 500


def test_upload_images_other_user(c, users, flights):
    _auth(c, users[1])
    resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 403


def test_upload_images_admin(c, users, flights, fs):
    _auth(c, users[2])
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid), "")
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/commit/" + str(flights[0].uuid), "")
    resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200


class MockImage:
    def thumbnail(self, size):
        assert size == (512, 512)
        return self

    def save(self, out_path, format):
        assert format == "PNG"
        return self

    def putalpha(self, mask):
        assert isinstance(mask, MockImage)
        return self

    def split(self):
        return [self]


def _test_webhook(c, monkeypatch, fs, flight, code):
    executed = [False, False]

    def _mark_executed(i, response_headers):
        nonlocal executed
        executed[i] = True
        return [200, response_headers, ""]

    def mark_executed_upload(request, uri, response_headers):
        return _mark_executed(0, response_headers)

    def mark_executed_config(request, uri, response_headers):
        return _mark_executed(1, response_headers)

    httpretty.register_uri(httpretty.POST, "http://container-nginx/geoserver/geoserver/rest/workspaces", "")
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/flight_" +
                           str(flight.uuid) + "/coveragestores/ortho/external.geotiff", mark_executed_upload)
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/flight_" +
                           str(flight.uuid) + "/coveragestores/ortho/coverages/rgb.json", mark_executed_config)
    png_created = False
    annotated_png_created = False
    thumbnail_created = False

    def mock_png_ortho(*args, **kwargs):
        nonlocal png_created
        png_created = True

    def mock_annotated_png_ortho(*args, **kwargs):
        nonlocal annotated_png_created
        annotated_png_created = True

    def mock_thumbnail(*args, **kwargs):
        nonlocal thumbnail_created
        thumbnail_created = True

    from core.models import Flight
    # monkeypatch.setattr(Flight, "try_create_annotated_png_ortho", mock_annotated_png_ortho)
    fs.create_dir("/flights/{}/odm_orthophoto".format(flight.uuid))
    fs.create_file("/flights/{}/odm_orthophoto/rgb.tif".format(flight.uuid), contents="")
    fs.create_file("/flights/{}/odm_orthophoto/rgb.tif.msk".format(flight.uuid), contents="")
    fs.create_file("/flights/{}/images.json".format(flight.uuid), contents="[]")

    def mock_open(*args, **kwargs):
        return MockImage()

    def mock_subprocess(*args, **kwargs):
        class FakeStdout:
            @staticmethod
            def decode(encoding):
                assert encoding == "utf-8"
                return "PROJ.4 string is:\n'+proj=longlat +datum=WGS84 +no_defs'\n" \
                       "Origin = (0.0,0.0)\nPixel Size = (1.0,1.0)"

        class FakeSubprocessCall:
            stdout = FakeStdout()

        assert "gdalinfo" == args[0][0]
        return FakeSubprocessCall()

    def donothing(*args, **kwargs):
        pass

    def mock_figure(*args, **kwargs):
        class MockCanvas:
            def draw(self):
                pass

            @staticmethod
            def tostring_rgb():
                return ""

            @staticmethod
            def get_width_height():
                return (100, 200)

        class MockFigure:
            canvas = MockCanvas()

        return MockFigure()

    def mock_fromstring(*args, **kwargs):
        class FakeNumpy:
            def reshape(self, new_shape):
                assert new_shape == (200, 100, 3) # Reverse X and Y, add a 3 for RGB channels
                return self

        return FakeNumpy()

    monkeypatch.setattr(Image, "open", mock_open)
    monkeypatch.setattr(ImageOps, "fit", mock_open)
    import matplotlib, numpy
    monkeypatch.setattr(matplotlib.pyplot, "imread", donothing)
    monkeypatch.setattr(matplotlib.pyplot, "figure", mock_figure)
    monkeypatch.setattr(matplotlib.pyplot, "axis", donothing)
    monkeypatch.setattr(matplotlib.pyplot, "imshow", donothing)
    monkeypatch.setattr(matplotlib.pyplot, "imsave", donothing)
    monkeypatch.setattr(numpy, "fromstring", mock_fromstring)
    import subprocess
    monkeypatch.setattr(subprocess, "run", mock_subprocess)
    resp = c.post(reverse("webhook"), json.dumps(
        {"uuid": str(flight.uuid), "status": {"code": code}}), content_type="application/text")
    if code == 40:
        assert all(executed)
        # assert annotated_png_created
        # assert thumbnail_created
        # assert png_created
    return resp


def test_webhook_successful(c, monkeypatch, fs, flights):
    resp = _test_webhook(c, monkeypatch, fs, flights[0], code=40)
    assert resp.status_code == 200
    flights[0].refresh_from_db()  # HACK seems to be necessary to reload status?
    assert flights[0].state == FlightState.COMPLETE.name
    # TODO maybe assert that the Geoserver APIs are called, if possible


def test_webhook_with_error(c, monkeypatch, fs, flights):
    resp = _test_webhook(c, monkeypatch, fs, flights[0], code=30)
    assert resp.status_code == 200
    flights[0].refresh_from_db()
    assert flights[0].state == FlightState.ERROR.name


def test_webhook_canceled(c, monkeypatch, fs, flights):
    resp = _test_webhook(c, monkeypatch, fs, flights[0], code=50)
    assert resp.status_code == 200
    flights[0].refresh_from_db()
    assert flights[0].state == FlightState.CANCELED.name


def test_download_artifact(c, flights, fs):
    uuid = str(flights[0].uuid)
    fs.create_file("/flights/" + uuid + "/odm_orthophoto/odm_orthophoto.png", contents="PNG orthomosaic")
    fs.create_file("/flights/" + uuid + "/odm_orthophoto/odm_orthophoto_annotated.png", contents="the annotated ortho")
    fs.create_file("/flights/" + uuid + "/odm_orthophoto/odm_orthophoto.tif", contents="barbaz")
    fs.create_file("/flights/" + uuid + "/odm_meshing/odm_mesh.ply", contents="the 3d mesh")
    fs.create_file("/flights/" + uuid + "/odm_dem/dsm_colored_hillshade.png", contents="the dsm")
    fs.create_file("/flights/" + uuid + "/odm_texturing/odm_textured_model.obj", contents="the texture")
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "orthomosaic.png"}))
    # Iterator juggling, streaming_content must be forced to return its first value
    assert next(resp.streaming_content).decode("utf-8") == "PNG orthomosaic"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "orthomosaic.tiff"}))
    assert next(resp.streaming_content).decode("utf-8") == "barbaz"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "3dmodel"}))
    assert next(resp.streaming_content).decode("utf-8") == "the 3d mesh"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "dsm.png"}))
    assert next(resp.streaming_content).decode("utf-8") == "the dsm"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "orthomosaic.annotated.png"}))
    assert next(resp.streaming_content).decode("utf-8") == "the annotated ortho"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "3dmodel_texture"}))
    assert next(resp.streaming_content).decode("utf-8") == "the texture"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "someunknownartifact"}))
    assert resp.status_code == 404


def test_download_report(c, flights, fs, monkeypatch):
    uuid = str(flights[0].uuid)
    report_invoked = False

    def mock_report(*args, **kwargs):
        nonlocal report_invoked
        report_invoked = True
        return "/flights/" + uuid + "/report.pdf"

    monkeypatch.setattr(Flight, "create_report", mock_report)
    fs.create_file("/flights/" + uuid + "/report.pdf", contents="the report")
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "report.pdf"}))
    assert next(resp.streaming_content).decode("utf-8") == "the report"

    assert report_invoked


def test_formula_checker_endpoint(c):
    assert c.post(reverse("check_formula"), {"formula": "(red+  blue)"}).status_code == 200
    assert c.post(reverse("check_formula"), {"formula": "(red+  blue"}).status_code == 400
    assert c.post(reverse("check_formula"), {"formula": "foobar"}).status_code == 400


def test_save_push_device(c):
    User = get_user_model()
    u1 = User.objects.create_user(username="u1", email="u1@example.com", password="u1")
    assert c.post(reverse("push_devices",
                          kwargs={"device": "android"}),
                  {"username": "u1", "token": "dummyToken"}).status_code == 200
    assert c.post(reverse("push_devices",
                          kwargs={"device": "android"}),
                  {"username": "u3", "token": "dummyToken"}).status_code == 400
