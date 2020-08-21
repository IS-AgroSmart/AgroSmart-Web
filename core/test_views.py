import inspect
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
import pytest_django.asserts as asserts

from core.models import FlightState, UserType, Flight, Camera, UserProject, ArtifactType, Artifact

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
def projects(users, flights):
    httpretty.enable()
    httpretty.register_uri(httpretty.POST, "http://container-nginx/geoserver/geoserver/rest/workspaces", "")
    p1 = users[0].user_projects.create(name="proj1")
    p1.flights.add(flights[0])
    return p1,


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
        # intentionally empty
        pass

    def mock_figure(*args, **kwargs):
        class MockCanvas:
            def draw(self):
                # intentionally empty
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
                assert new_shape == (200, 100, 3)  # Reverse X and Y, add a 3 for RGB channels
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


def _test_upload_vector(c, fs, project, type):
    from django.core.files.uploadedfile import SimpleUploadedFile

    executed = [False, False]

    def _mark_executed(i, response_headers):
        nonlocal executed
        executed[i] = True
        return [200, response_headers, ""]

    def mark_executed_a(request, uri, response_headers):
        return _mark_executed(0, response_headers)

    def mark_executed_b(request, uri, response_headers):
        return _mark_executed(1, response_headers)

    f = SimpleUploadedFile("file.{}".format(type), b"myfile")
    fs.create_dir("/projects/{}/file/".format(project.uuid))
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/project_" +
                           str(project.uuid) + "/datastores/file/external.shp", mark_executed_a)
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/project_" +
                           str(project.uuid) + "/datastores/file/featuretypes/file.json", mark_executed_b)

    resp = c.post(reverse("upload_vector", kwargs={"uuid": str(project.uuid)}),
                  {"datatype": type, "file": f if type == "kml" else [f, f, f], "title": "myVector"})

    assert len(project.artifacts.all()) == 1
    assert all(executed)
    assert project.artifacts.first().type == ArtifactType.SHAPEFILE.name
    assert resp.status_code == 201


def test_upload_vector_kml(c, fs, projects):
    _test_upload_vector(c, fs, projects[0], "kml")


def test_upload_vector_shp(c, fs, projects):
    _test_upload_vector(c, fs, projects[0], "shp")


def test_upload_geotiff(c, fs, projects):
    from django.core.files.uploadedfile import SimpleUploadedFile

    executed = [False, False]

    def _mark_executed(i, response_headers):
        nonlocal executed
        executed[i] = True
        return [200, response_headers, ""]

    def mark_executed_a(request, uri, response_headers):
        return _mark_executed(0, response_headers)

    def mark_executed_b(request, uri, response_headers):
        return _mark_executed(1, response_headers)

    project: UserProject = projects[0]
    f = SimpleUploadedFile("file.tif", b"myfile")
    fs.create_dir("/projects/{}/file/".format(project.uuid))
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/project_" +
                           str(project.uuid) + "/coveragestores/file/external.geotiff", mark_executed_a)
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/project_" +
                           str(project.uuid) + "/coveragestores/file/coverages/file.json", mark_executed_b)

    resp = c.post(reverse("upload_geotiff", kwargs={"uuid": str(project.uuid)}),
                  {"geotiff": f, "title": "myKML"})

    assert len(project.artifacts.all()) == 1
    assert all(executed)
    assert project.artifacts.first().type == ArtifactType.ORTHOMOSAIC.name
    assert resp.status_code == 201


def test_upload_index(c, fs, flights, projects):
    project: UserProject = projects[0]
    flight: Flight = flights[0]
    flight.state = FlightState.COMPLETE.name
    flight.save()
    fs.create_dir("/projects/{}".format(project.uuid))
    fs.create_file("/flights/{}/odm_orthophoto/my_index.tif".format(flight.uuid))
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/project_" +
                           str(project.uuid) + "/coveragestores/my_index/external.imagemosaic", "")
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/workspaces/project_" +
                           str(project.uuid) + "/coveragestores/my_index/coverages/my_index.json", "")
    httpretty.register_uri(httpretty.PUT, "http://container-nginx/geoserver/geoserver/rest/layers/project_" +
                           str(project.uuid) + ":my_index.json", "")
    resp = c.post(reverse("create_raster_index", kwargs={"uuid": str(project.uuid)}),
                  json.dumps({"index": "my_index", "formula": "red+1"}), content_type="application/text")
    assert resp.status_code == 200


def test_preview_flight_url(c, flights):
    executed = False

    def mark_executed(request, uri, response_headers):
        nonlocal executed
        executed = True
        resp = json.dumps({"coverage": {
            "nativeBoundingBox": {
                "minx": 0,
                "maxx": 1,
                "miny": 10,
                "maxy": 11
            },
            "srs": "fakeSRS"
        }})
        return [200, response_headers, resp]

    flight: Flight = flights[0]
    httpretty.register_uri(httpretty.GET, "http://container-nginx/geoserver/geoserver/rest/workspaces/flight_" +
                           str(flight.uuid) + "/coveragestores/ortho/coverages/odm_orthophoto.json", mark_executed)

    resp = c.get(reverse("preview_flight_url", kwargs={"uuid": str(flight.uuid)}))
    assert resp.status_code == 200
    assert "url" in resp.json()
    assert executed


def test_email_send():
    from core.views import password_reset_token_created

    class MockPwdResetToken:
        class MockUser:
            username = "username"
            email = "myemail@example.com"

        user = MockUser()
        key = "tokenkey"

    import core

    from unittest.mock import Mock, ANY, create_autospec
    mock = create_autospec(core.views.EmailMultiAlternatives)
    core.views.EmailMultiAlternatives = Mock(return_value=mock)
    password_reset_token_created(None, None, MockPwdResetToken())

    mock.attach_alternative.assert_called_with(ANY, "text/html")
    mock.send.assert_called()


def _test_mapper_serve_static(c, fs, url, filename, contents):
    fs.create_file(filename, contents=contents)
    resp = c.get(url)
    assert next(resp.streaming_content).decode("utf-8") == contents


def test_mapper_serve_paneljs(c, fs):
    _test_mapper_serve_static(c, fs, "/mapper/panel.js", "templates/geoext/examples/tree/panel.js", "thepaneljs")


def test_mapper_serve_ticks(c, fs):
    _test_mapper_serve_static(c, fs, "/mapper/ticks/3", "templates/geoext/examples/tree/3ticks.png", "3ticks")


def test_mapper_ol(c, fs):
    _test_mapper_serve_static(c, fs, "/mapper/ol/foo/bar.css", "templates/geoext/examples/lib/ol/foo/bar.css", "CSS")


def test_mapper_src(c, fs):
    _test_mapper_serve_static(c, fs, "/mapper/geoext/src/foo/bar.css", "templates/geoext/src/foo/bar.css", "geoextCSS")


def test_mapper_get_indices_list(c, projects):
    project: UserProject = projects[0]
    art1 = Artifact(title="My Artifact", type=ArtifactType.INDEX.name, name="myartifact")
    art1.save()
    art2 = Artifact(title="My Unwanted Artifact", type=ArtifactType.SHAPEFILE.name, name="foo")
    art2.save()
    project.artifacts.add(art1)
    project.artifacts.add(art2)
    resp = c.get(reverse("mapper_indices", kwargs={"uuid": str(project.uuid)}))
    assert resp.status_code == 200
    data = resp.json()
    assert "indices" in data
    assert len(data["indices"]) == 1
    assert data["indices"][0]["title"] == "My Artifact"
    assert data["indices"][0]["name"] == "myartifact"


def test_mapper_get_shp_and_geotiff_list(c, projects):
    project: UserProject = projects[0]
    art1 = Artifact(title="My Unwanted Artifact", type=ArtifactType.INDEX.name, name="myartifact")
    art1.save()
    art2 = Artifact(title="My Artifact", type=ArtifactType.SHAPEFILE.name, name="foo")
    art2.save()
    project.artifacts.add(art1)
    project.artifacts.add(art2)
    resp = c.get(reverse("mapper_artifacts", kwargs={"uuid": str(project.uuid)}))
    assert resp.status_code == 200
    data = resp.json()
    assert "artifacts" in data
    assert len(data["artifacts"]) == 2
    assert "My Artifact" in [x["name"] for x in data["artifacts"]]


def test_mapper_bbox(c, projects):
    project: UserProject = projects[0]
    bbox = json.dumps({"coverage": {"nativeBoundingBox": 123, "srs": "fakeSRS"}, "something": "else"})
    httpretty.register_uri(httpretty.GET, "http://container-nginx/geoserver/geoserver/rest/workspaces/project_" +
                           str(project.uuid) + "/coveragestores/mainortho/coverages/mainortho.json", body=bbox)
    resp = c.get(reverse("mapper_bbox", kwargs={"uuid": str(project.uuid)}))
    assert resp.status_code == 200
    data = resp.json()
    assert data["bbox"] == 123
    assert data["srs"] == "fakeSRS"

# def test_mapper_html(c, projects):
#     project: UserProject = projects[0]
#     from unittest.mock import Mock, ANY, create_autospec
#     import core.views
#     mock = create_autospec(core.views.render)
#     core.views.render = Mock(return_value=mock)
#
#     resp = c.get(reverse("mapper", kwargs={"uuid": str(project.uuid)}))
#     mock.assert_called_with(ANY, "geoext/examples/tree/panel.html", ANY)
