import inspect
import json
import os
import re
from datetime import datetime
from typing import List

import pytest
from PIL import Image, ImageOps, ImageFont, ImageDraw
from django.urls import reverse
from httpretty import httpretty
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import FlightState, UserType, Flight, Camera, UserProject, ArtifactType, Artifact, User


class MockFont:
    pass


class MockDraw:
    @staticmethod
    def textsize(text: str, font: MockFont):
        del (text,)  # unused
        assert isinstance(font, MockFont)
        return 100, 10

    @staticmethod
    def text(pos, text, color, font):
        del (pos, text, color)  # unused
        assert isinstance(font, MockFont)


class MockImage:
    def thumbnail(self, size):
        assert size == (512, 512)
        return self

    def resize(self, xy):
        del (xy,)  # unused
        return self

    def save(self, out_path: str, fmt: str):
        assert out_path.endswith(".png")
        assert fmt == "PNG"
        return self

    def putalpha(self, mask):
        assert isinstance(mask, MockImage)
        return self

    def paste(self, another, xy):
        del (xy,)  # unused
        assert isinstance(another, MockImage)
        return self

    def split(self):
        return [self]

    def putpixel(self, xy, color):
        del (color,)  # unused
        assert xy[1] == 0
        return self


@pytest.mark.django_db
class TestStandaloneViews:
    @pytest.fixture
    def users(self, fs):
        from pyfakefs.fake_filesystem_unittest import Pause
        with Pause(fs):
            # Pause(fs) stops the fake filesystem and allows Django access to the common password list
            u1 = User.objects.create_user(username="u1", email="u1@example.com", password="u1", remaining_images=20)
            u2 = User.objects.create_user(username="u2", email="u2@example.com", password="u2")
            admin = User.objects.create_user(username="admin", email="admin@example.com", password="admin",
                                             type=UserType.ADMIN.name)

            Token.objects.create(user=u1)
            Token.objects.create(user=u2)
            Token.objects.create(user=admin)
            return u1, u2, admin

    @pytest.fixture
    def flights(self, users):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/init")
        httpretty.register_uri(httpretty.POST, re.compile(r"http://container-webhook-adapter:8080/register/.+"))
        f1 = users[0].flight_set.create(name="flight1", date=datetime.now())
        f1.camera = Camera.REDEDGE.name
        f1.save()
        return f1,

    @pytest.fixture
    def projects(self, users, flights):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://container-geoserver:8080/geoserver/rest/workspaces", "")
        p1 = users[0].user_projects.create(name="proj1")
        p1.flights.add(flights[0])
        return p1,

    @pytest.fixture
    def c(self):
        return APIClient()

    @staticmethod
    def _auth(c, user):
        token = Token.objects.get(user=user)
        c.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def _test_upload_two_images(self, c, fs, users, flights):
        """
        A helper function to send a POST request to the upload image view, with a couple of images
        Args:
            c: The APICLient fixture
            fs: The pyfakefs fixture
            users: A fixture containing pregenerated Users
            flights: A fixture containing pregenerated Flights
        """
        self._auth(c, users[0])
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid),
                               "")
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/commit/" + str(flights[0].uuid),
                               "")
        import django
        import pytz
        fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
        fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
        fs.create_file("/tmp/image1.jpg", contents="foobar")
        fs.create_file("/tmp/image2.jpg", contents="foobar")
        with open("/tmp/image1.jpg") as f1, open("/tmp/image2.jpg") as f2:
            return c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}), {"images": [f1, f2]})

    # @pytest.mark.xfail(reason="pyfakefs limitation on /tmp dir")
    def test_upload_images_succesful(self, c, users, flights, fs):
        """
        Tests that the upload view succeds if all is well
        Args:
            c: The APICLient fixture
            users: A fixture containing pregenerated Users
            flights: A fixture containing pregenerated Flights
            fs: The pyfakefs fixture
        """
        assert users[0].remaining_images == 20

        resp = self._test_upload_two_images(c, fs, users, flights)

        assert resp.status_code == 200
        users[0].refresh_from_db()
        assert users[0].remaining_images == 18

    def test_upload_images_error_on_creation(self, c, users, flights, fs):
        import inspect
        import django
        import pytz

        self._auth(c, users[0])
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid),
                               "",
                               status=500)
        fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
        fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
        resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
        assert resp.status_code == 500

    def test_upload_images_error_on_commit(self, c, users, flights, fs):
        import inspect
        import django
        import pytz

        self._auth(c, users[0])
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid),
                               "")
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/commit/" + str(flights[0].uuid),
                               "",
                               status=500)
        fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
        fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
        resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
        assert resp.status_code == 500

    def test_upload_images_other_user(self, c, users, flights):
        self._auth(c, users[1])
        resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
        assert resp.status_code == 403

    def test_upload_images_admin(self, c, users, flights, fs):
        self._auth(c, users[2])
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/upload/" + str(flights[0].uuid),
                               "")
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/commit/" + str(flights[0].uuid),
                               "")
        resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
        assert resp.status_code == 200

    def test_upload_images_user_disk_full(self, c, fs, users: List[User], flights):
        """
        Tests that image upload fails if the user is over his disk quota
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            users: A fixture containing some pre-created Users
            flights: A fixture containing some pre-created Flights
        """
        users[0].used_space = 50 * 1024 ** 2  # 50GB used
        users[0].save()
        users[0].refresh_from_db()
        assert users[0].used_space > users[0].maximum_space

        resp = self._test_upload_two_images(c, fs, users, flights)

        assert resp.status_code == 402

    def test_upload_images_not_enough_images(self, c, fs, users: List[User], flights):
        """
        Tests that image upload fails if the user is over his monthly image quota
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            users: A fixture containing some pre-created Users
            flights: A fixture containing some pre-created Flights
        """
        users[0].remaining_images = 1
        users[0].save()
        users[0].refresh_from_db()

        resp = self._test_upload_two_images(c, fs, users, flights)

        assert resp.status_code == 402
        assert resp.content.decode("utf8") == "Subida fallida. Tiene un límite de 1 imágenes."

    def _test_webhook(self, c, monkeypatch, fs, flight, false_code, real_code):
        """
        Helper function that tests the webhook with configurable behavior
        Args:
            c: The HTTP client fixture
            monkeypatch: The monkeypatch fixture
            fs: The pyfakefs fixture
            flight: A Flight object to test the webhook on
            false_code: The status code that will be in the webhook POST data
                (false_code because it should NOT be trusted, as anybody can send a webhook request)
            real_code: The status code that will be returned by NodeODM (real_code because it's The Final Truth,
                and unforgeable from the outside)

        Returns: The status code returned by the webhook view
        """
        executed = [False] * 3

        def _mark_executed(i, response_headers):
            nonlocal executed
            executed[i] = True
            return [200, response_headers, ""]

        def mark_executed_download_results(*args, **kwargs):
            del (args, kwargs)  # unused
            _mark_executed(0, None)

        def get_real_info(request, uri, response_headers):
            del (request,)  # unused
            assert str(flight.uuid) in uri
            data = {
                "uuid": str(flight.uuid),
                "status": {"code": real_code},
                "processingTime": 12345,
                "imagesCount": 31
            }
            return [200, response_headers, json.dumps(data)]

        def mark_executed_upload(request, uri, response_headers):
            del (request, uri)  # unused
            return _mark_executed(1, response_headers)

        def mark_executed_config(request, uri, response_headers):
            del (request, uri)  # unused
            return _mark_executed(2, response_headers)

        httpretty.register_uri(httpretty.GET,
                               "http://container-nodeodm:3000/task/{}/download/all.zip".format(flight.uuid),
                               mark_executed_download_results)
        httpretty.register_uri(httpretty.GET, "http://container-nodeodm:3000/task/{}/info".format(flight.uuid),
                               get_real_info)
        monkeypatch.setattr(Flight, "download_and_decompress_results", mark_executed_download_results)
        httpretty.register_uri(httpretty.POST, "http://container-geoserver:8080/geoserver/rest/workspaces", "")
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/flight_" +
                               str(flight.uuid) + "/coveragestores/ortho/external.geotiff", mark_executed_upload)
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/flight_" +
                               str(flight.uuid) + "/coveragestores/ortho/coverages/rgb.json", mark_executed_config)

        fs.create_dir("/flights/{}/odm_orthophoto".format(flight.uuid))
        fs.create_file("/flights/{}/odm_orthophoto/rgb.tif".format(flight.uuid), contents="A" * 1024 * 1024)
        fs.create_file("/flights/{}/odm_orthophoto/rgb.tif.msk".format(flight.uuid), contents="")
        fs.create_file("/flights/{}/odm_orthophoto/odm_orthophoto_small.tif".format(flight.uuid), contents="")
        fs.create_file("/flights/{}/images.json".format(flight.uuid), contents="[]")

        def mock_create_image(*args, **kwargs):
            del (args, kwargs)  # unused
            return MockImage()

        def mock_create_font(*args, **kwargs):
            del (kwargs,)  # unused
            assert args[0] == "DejaVuSans.ttf"
            return MockFont()

        def mock_create_draw(*args, **kwargs):
            del (kwargs,)  # unused
            assert isinstance(args[0], MockImage)
            return MockDraw()

        def mock_subprocess(*args, **kwargs):
            del (kwargs,)  # unused

            class FakeStdout:
                @staticmethod
                def decode(encoding):
                    assert encoding == "utf-8"
                    return "PROJ.4 string is:\n'+proj=longlat +datum=WGS84 +no_defs'\n" \
                           "Origin = (0.0,0.0)\nPixel Size = (1.0,1.0)\n" \
                           "Computed Min/Max=0.0,1.0"

            class FakeSubprocessCall:
                stdout = FakeStdout()

            assert "gdalinfo" == args[0][0]
            return FakeSubprocessCall()

        def donothing(*args, **kwargs):
            del (args, kwargs)  # unused
            # intentionally empty

        def mock_figure(*args, **kwargs):
            del (args, kwargs)  # unused

            class MockCanvas:
                def draw(self):
                    # intentionally empty
                    pass

                @staticmethod
                def tostring_rgb():
                    return ""

                @staticmethod
                def get_width_height():
                    return 100, 200

            class MockFigure:
                canvas = MockCanvas()

            return MockFigure()

        def mock_fromstring(*args, **kwargs):
            del (args, kwargs)  # unused

            class FakeNumpy:
                def reshape(self, new_shape):
                    assert new_shape == (200, 100, 3)  # Reverse X and Y, add a 3 for RGB channels
                    return self

            return FakeNumpy()

        monkeypatch.setattr(Image, "open", mock_create_image)
        monkeypatch.setattr(Image, "new", mock_create_image)
        monkeypatch.setattr(ImageFont, "truetype", mock_create_font)
        monkeypatch.setattr(ImageOps, "fit", mock_create_image)
        monkeypatch.setattr(ImageDraw, "Draw", mock_create_draw)
        import matplotlib
        import numpy
        monkeypatch.setattr(matplotlib.pyplot, "imread", donothing)
        monkeypatch.setattr(matplotlib.pyplot, "figure", mock_figure)
        monkeypatch.setattr(matplotlib.pyplot, "axis", donothing)
        monkeypatch.setattr(matplotlib.pyplot, "imshow", donothing)
        monkeypatch.setattr(matplotlib.pyplot, "imsave", donothing)
        monkeypatch.setattr(numpy, "fromstring", mock_fromstring)
        import subprocess
        monkeypatch.setattr(subprocess, "run", mock_subprocess)
        resp = c.post(reverse("webhook"), json.dumps(
            {"uuid": str(flight.uuid), "status": {"code": false_code}}), content_type="application/text")
        if real_code == 40:
            assert all(executed)
        else:
            assert not any(executed)
        return resp

    def test_webhook_successful(self, c, monkeypatch, fs, flights):
        resp = self._test_webhook(c, monkeypatch, fs, flights[0], false_code=40, real_code=40)

        assert resp.status_code == 200
        flights[0].refresh_from_db()
        assert flights[0].state == FlightState.COMPLETE.name
        flights[0].user.refresh_from_db()
        # NodeODM reports Flight has 31 images, but they should NOT get returned if the task ends OK
        assert flights[0].user.remaining_images == 20

    def test_webhook_with_error(self, c, monkeypatch, fs, flights):
        """
        Tests the case when the webhook is invoked with a failed flight
        Args:
            c: The APIClient fixture
            monkeypatch: The monkeypatch fixture
            fs: The pyfakefs fixture
            flights: A fixture containing pregenerated Flights
        """
        assert flights[0].user.remaining_images == 20

        resp = self._test_webhook(c, monkeypatch, fs, flights[0], false_code=30, real_code=30)

        assert resp.status_code == 200
        flights[0].refresh_from_db()
        assert flights[0].state == FlightState.ERROR.name
        flights[0].user.refresh_from_db()
        assert flights[0].user.remaining_images == 51  # NodeODM reports Flight has 31 images

    def test_webhook_canceled(self, c, monkeypatch, fs, flights):
        resp = self._test_webhook(c, monkeypatch, fs, flights[0], false_code=50, real_code=50)
        assert resp.status_code == 200
        flights[0].refresh_from_db()
        assert flights[0].state == FlightState.CANCELED.name

    def test_webhook_doesnt_trust_webhook_data(self, c, monkeypatch, fs, flights):
        resp = self._test_webhook(c, monkeypatch, fs, flights[0], false_code=50, real_code=40)
        assert resp.status_code == 200
        flights[0].refresh_from_db()
        assert flights[0].state == FlightState.COMPLETE.name  # Should be COMPLETE (40), not CANCELED (50)
        # This time comes from the REAL API call, the webhook POST has no processing time
        # Therefore, if time is actually 12345, then the webhook is trusting the real data
        assert flights[0].processing_time == 12345

    def test_webhook_updates_used_disk(self, c, monkeypatch, fs, flights: List[Flight]):
        assert flights[0].user.used_space == 0
        self._test_webhook(c, monkeypatch, fs, flights[0], false_code=40, real_code=40)
        flights[0].refresh_from_db()
        flights[0].user.refresh_from_db()

        assert flights[0].used_space == 1024  # 1MB used by flight
        assert flights[0].user.used_space == flights[0].used_space

    def test_webhook_doesnt_update_disk_on_failed(self, c, monkeypatch, fs, flights: List[Flight]):
        assert flights[0].user.used_space == 0
        self._test_webhook(c, monkeypatch, fs, flights[0], false_code=50, real_code=50)
        flights[0].refresh_from_db()
        flights[0].user.refresh_from_db()

        assert flights[0].used_space == 0  # 1MB used by flight
        assert flights[0].user.used_space == 0

    def test_download_artifact(self, c, flights, fs):
        uuid = str(flights[0].uuid)
        fs.create_file("/flights/" + uuid + "/odm_orthophoto/odm_orthophoto.png", contents="PNG orthomosaic")
        fs.create_file("/flights/" + uuid + "/odm_orthophoto/odm_orthophoto_annotated.png",
                       contents="the annotated ortho")
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

    def test_download_report(self, c, flights, fs, monkeypatch):
        uuid = str(flights[0].uuid)
        report_invoked = False

        def mock_report(*args, **kwargs):
            del (args, kwargs)  # unused
            nonlocal report_invoked
            report_invoked = True
            return "/flights/" + uuid + "/report.pdf"

        monkeypatch.setattr(Flight, "create_report", mock_report)
        fs.create_file("/flights/" + uuid + "/report.pdf", contents="the report")
        resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "report.pdf"}))
        assert next(resp.streaming_content).decode("utf-8") == "the report"

        assert report_invoked

    def test_formula_checker_endpoint(self, c):
        assert c.post(reverse("check_formula"), {"formula": "(red+  blue)"}).status_code == 200
        assert c.post(reverse("check_formula"), {"formula": "(red+  blue"}).status_code == 400
        assert c.post(reverse("check_formula"), {"formula": "foobar"}).status_code == 400

    def test_save_push_device(self, c):
        User.objects.create_user(username="u1", email="u1@example.com", password="u1")
        assert c.post(reverse("push_devices",
                              kwargs={"device": "android"}),
                      {"username": "u1", "token": "dummyToken"}).status_code == 200
        assert c.post(reverse("push_devices",
                              kwargs={"device": "android"}),
                      {"username": "u3", "token": "dummyToken"}).status_code == 400

    @staticmethod
    def _test_upload_vector(c, fs, project, type, should_succeed=True):
        from django.core.files.uploadedfile import SimpleUploadedFile

        executed = [False, False]

        def _mark_executed(i, response_headers):
            nonlocal executed
            executed[i] = True
            return [200, response_headers, ""]

        def mark_executed_a(request, uri, response_headers):
            del (request, uri)  # unused
            return _mark_executed(0, response_headers)

        def mark_executed_b(request, uri, response_headers):
            del (request, uri)  # unused
            return _mark_executed(1, response_headers)

        kml_files = [SimpleUploadedFile(f"file2_{type}.{type}", b"A" * 1024 * 25)]
        shp_files = [SimpleUploadedFile(f"file2_{type}.{ext}", b"A" * 1024 * 25) for ext in ("shp", "shx", "dbf")]
        fs.create_dir(f"/projects/{project.uuid}/file2_{type}")
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/project_" +
                               str(project.uuid) + f"/datastores/file2_{type}/external.shp", mark_executed_a)
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/project_" +
                               str(project.uuid) + f"/datastores/file2_{type}/featuretypes/file2_{type}.json",
                               mark_executed_b)

        resp = c.post(reverse("upload_vector", kwargs={"uuid": str(project.uuid)}),
                      {"datatype": type, "file": kml_files if type == "kml" else shp_files, "title": "myVector"})
        if should_succeed:
            assert all(executed)
        return resp

    def test_upload_vector_kml(self, c, fs, projects: List[UserProject]):
        resp = self._test_upload_vector(c, fs, projects[0], "kml")

        assert len(projects[0].artifacts.all()) == 1
        assert projects[0].artifacts.first().type == ArtifactType.SHAPEFILE.name
        assert resp.status_code == 201
        projects[0].refresh_from_db()
        projects[0].user.refresh_from_db()
        assert projects[0].used_space == 25
        assert projects[0].user.used_space == 25

    def test_upload_vector_shp(self, c, fs, projects: List[UserProject]):
        """
        Tests the upload of a Shapefile (plus companion files) to a Project
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            projects: A fixture containing pregenerated Projects
        """
        resp = self._test_upload_vector(c, fs, projects[0], "shp")

        assert len(projects[0].artifacts.all()) == 1
        assert projects[0].artifacts.first().type == ArtifactType.SHAPEFILE.name
        assert resp.status_code == 201
        projects[0].refresh_from_db()
        projects[0].user.refresh_from_db()
        assert projects[0].used_space == 75  # 3 files (.shp, .shx, .dbf), each of 25KB
        assert projects[0].user.used_space == 75  # User only has one Project of 75KB

    def test_upload_vector_over_quota(self, c, fs, projects: List[UserProject]):
        """
        Tests that uploading a vector file fails if User is over his disk quota
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            projects: A fixture containing pregenerated Projects
        """
        projects[0].user.used_space = 50 * 1024 ** 2
        projects[0].user.save()
        resp = self._test_upload_vector(c, fs, projects[0], "kml", should_succeed=False)

        assert resp.status_code == 402
        projects[0].refresh_from_db()
        projects[0].user.refresh_from_db()
        assert projects[0].used_space == 0  # no extra disk space should be used!
        assert projects[0].user.used_space == 50 * 1024 ** 2

    @staticmethod
    def _upload_geotiff(c, fs, projects, should_succeed=True):
        """
        Helper function to upload a GeoTIFF to a Project
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            projects: A fixture containing pregenerated Projects
            should_succeed: True if the creation request should be successful
        """
        from django.core.files.uploadedfile import SimpleUploadedFile
        executed = [False, False]

        def _mark_executed(i, response_headers):
            nonlocal executed
            executed[i] = True
            return [200, response_headers, ""]

        def mark_executed_a(request, uri, response_headers):
            del (request, uri)  # unused
            return _mark_executed(0, response_headers)

        def mark_executed_b(request, uri, response_headers):
            del (request, uri)  # unused
            return _mark_executed(1, response_headers)

        project: UserProject = projects[0]
        f = SimpleUploadedFile("file.tiff", b"G" * 1024 ** 2)
        fs.create_dir("/projects/{}/file/".format(project.uuid))
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/project_" +
                               str(project.uuid) + "/coveragestores/file/external.geotiff", mark_executed_a)
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/project_" +
                               str(project.uuid) + "/coveragestores/file/coverages/file.json", mark_executed_b)
        resp = c.post(reverse("upload_geotiff", kwargs={"uuid": str(project.uuid)}),
                      {"geotiff": f, "title": "myKML"})

        if should_succeed:
            assert all(executed)
        return resp

    def test_upload_geotiff(self, c, fs, projects):
        """
        Tests uploading a GeoTIFF in the successful case
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            projects: A fixture containing pregenerated Projects
        """
        resp = self._upload_geotiff(c, fs, projects)

        assert len(projects[0].artifacts.all()) == 1
        assert projects[0].artifacts.first().type == ArtifactType.ORTHOMOSAIC.name
        assert resp.status_code == 201

        projects[0].refresh_from_db()
        projects[0].user.refresh_from_db()
        assert projects[0].used_space == 1024
        assert projects[0].user.used_space == 1024

    def test_upload_geotiff_over_quota(self, c, fs, projects):
        """
        Tests that uploading a GeoTIFF to a Project fails if the User is over his disk quota
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            projects: A fixture containing pregenerated Projects
        """
        projects[0].user.used_space = 50 * 1024 ** 2
        projects[0].user.save()
        resp = self._upload_geotiff(c, fs, projects, should_succeed=False)

        assert resp.status_code == 402
        projects[0].refresh_from_db()
        projects[0].user.refresh_from_db()
        assert projects[0].used_space == 0
        assert projects[0].user.used_space == 50 * 1024 ** 2

    @staticmethod
    def _upload_index(c, fs, flights, projects):
        """
        Helper function to upload a raster index to a Project
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            flights: A fixture containing pregenerated Projects
            projects: A fixture containing pregenerated Projects
        """
        project: UserProject = projects[0]
        flight: Flight = flights[0]
        flight.state = FlightState.COMPLETE.name
        flight.save()
        fs.create_dir("/projects/{}".format(project.uuid))
        fs.create_file("/flights/{}/odm_orthophoto/my_index.tif".format(flight.uuid), contents="A" * 1024 ** 2)
        import django
        import lark
        fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
        fs.add_real_directory(os.path.dirname(inspect.getfile(lark)))
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/project_" +
                               str(project.uuid) + "/coveragestores/my_index/external.imagemosaic", "")
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/workspaces/project_" +
                               str(project.uuid) + "/coveragestores/my_index/coverages/my_index.json", "")
        httpretty.register_uri(httpretty.PUT, "http://container-geoserver:8080/geoserver/rest/layers/project_" +
                               str(project.uuid) + ":my_index.json", "")
        resp = c.post(reverse("create_raster_index", kwargs={"uuid": str(project.uuid)}),
                      json.dumps({"index": "my_index", "formula": "red+1"}), content_type="application/text")
        return resp

    def test_upload_index(self, c, fs, flights, projects):
        """
        Tests uploading a raster index in the successful case
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            flights: A fixture containing pregenerated Projects
            projects: A fixture containing pregenerated Projects
        """
        resp = self._upload_index(c, fs, flights, projects)
        assert resp.status_code == 200

        projects[0].refresh_from_db()
        projects[0].user.refresh_from_db()
        assert projects[0].used_space == 1024  # 1MB for the fake index
        assert projects[0].user.used_space == 2048  # 1MB for the fake index in the Flight, same for the Project

    def test_upload_index_over_quota(self, c, fs, flights, projects):
        """
        Tests that uploading a raster index to a Project fails if the User is over his disk quota
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            flights: A fixture containing pregenerated Projects
            projects: A fixture containing pregenerated Projects
        """
        projects[0].user.used_space = 50 * 1024 ** 2
        projects[0].user.save()
        resp = self._upload_index(c, fs, flights, projects)

        assert resp.status_code == 402
        projects[0].refresh_from_db()
        projects[0].user.refresh_from_db()
        assert projects[0].used_space == 0
        assert projects[0].user.used_space == 50 * 1024 ** 2

    def test_preview_flight_url(self, c, flights):
        executed = False

        def mark_executed(request, uri, response_headers):
            del (request, uri)  # unused
            nonlocal executed
            executed = True
            _resp = json.dumps({"coverage": {
                "nativeBoundingBox": {
                    "minx": 0,
                    "maxx": 1,
                    "miny": 10,
                    "maxy": 11
                },
                "srs": "fakeSRS"
            }})
            return [200, response_headers, _resp]

        flight: Flight = flights[0]
        httpretty.register_uri(httpretty.GET, "http://container-geoserver:8080/geoserver/rest/workspaces/flight_" +
                               str(flight.uuid) + "/coveragestores/ortho/coverages/odm_orthophoto.json", mark_executed)

        resp = c.get(reverse("preview_flight_url", kwargs={"uuid": str(flight.uuid)}))
        assert resp.status_code == 200
        assert "url" in resp.json()
        assert executed

    def test_email_send(self):
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

    @staticmethod
    def _test_mapper_serve_static(c, fs, url, filename, contents):
        fs.create_file(filename, contents=contents)
        resp = c.get(url)
        assert next(resp.streaming_content).decode("utf-8") == contents

    def test_mapper_serve_paneljs(self, c, fs):
        self._test_mapper_serve_static(c, fs, "/mapper/panel.js", "templates/geoext/examples/tree/panel.js",
                                       "thepaneljs")

    def test_mapper_serve_ticks(self, c, fs):
        self._test_mapper_serve_static(c, fs, "/mapper/ticks/3", "templates/geoext/examples/tree/3ticks.png", "3ticks")

    def test_mapper_ol(self, c, fs):
        self._test_mapper_serve_static(c, fs, "/mapper/ol/foo/bar.css", "templates/geoext/examples/lib/ol/foo/bar.css",
                                       "CSS")

    def test_mapper_src(self, c, fs):
        self._test_mapper_serve_static(c, fs, "/mapper/geoext/src/foo/bar.css", "templates/geoext/src/foo/bar.css",
                                       "geoextCSS")

    def test_mapper_get_indices_list(self, c, projects):
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

    def test_mapper_get_shp_and_geotiff_list(self, c, projects):
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

    def test_mapper_bbox(self, c, projects):
        project: UserProject = projects[0]
        bbox = json.dumps({"coverage": {"nativeBoundingBox": 123, "srs": "fakeSRS"}, "something": "else"})
        httpretty.register_uri(httpretty.GET, "http://container-geoserver:8080/geoserver/rest/workspaces/project_" +
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
