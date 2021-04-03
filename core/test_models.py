import glob
from datetime import datetime
from typing import List

import pytest
from django.db import IntegrityError
from django.urls import reverse
from httpretty import httpretty

from core.models import *
from core.test_viewsets import FlightsMixin, BaseTestViewSet


class ProjectsMixin:
    @pytest.fixture
    def projects(self, users):
        p1 = users[0].user_projects.create(name="proj1")
        p2 = users[0].user_projects.create(name="proj2")
        return p1, p2


@pytest.mark.django_db
class TestUserProjectModel(FlightsMixin, ProjectsMixin, BaseTestViewSet):
    def test_disk_path(self, projects):
        assert projects[1].get_disk_path() == "/projects/" + str(projects[1].uuid)

    def test_workspace_name(self, projects: List[UserProject]):
        assert projects[0]._get_geoserver_ws_name() == "project_{}".format(projects[0].uuid)

    def test_all_flights_multispectral(self, projects, flights):
        projects[0].flights.add(flights[0], flights[1])
        assert projects[0].all_flights_multispectral()
        projects[1].flights.add(flights[0], flights[1], flights[2])
        assert not projects[1].all_flights_multispectral()

    def test_mainortho_creation_geoserver(self, c, users, flights, projects, monkeypatch, fs):
        c.force_authenticate(users[0])
        create_ws_executed = False
        put_requests = []

        def mark_create_ws_executed(request, uri, response_headers):
            del (request, uri)
            nonlocal create_ws_executed
            create_ws_executed = True
            return [200, response_headers, ""]

        def mock_requests_put(*args, **kwargs):
            nonlocal put_requests
            put_requests.append({"url": args[0], "headers": kwargs["headers"], "data": kwargs["data"]})

        httpretty.register_uri(httpretty.POST, "http://container-geoserver:8080/geoserver/rest/workspaces",
                               mark_create_ws_executed)
        import inspect
        import django
        import pytz
        fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
        fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
        fs.create_file("/flights/{}/odm_orthophoto/rgb.tif".format(flights[1].uuid), contents="")
        monkeypatch.setattr(requests, "put", mock_requests_put)

        resp = c.post(reverse('projects-list'), {"name": "foo", "description": "bar", "flights": flights[1].uuid})
        assert resp.status_code == 201
        assert create_ws_executed
        created_proj_uuid = resp.json()["uuid"]
        assert len(put_requests) == 2  # 2 PUT requests to Geoserver

        # Check first request
        assert "/workspaces/project_" + created_proj_uuid in put_requests[0]["url"]  # URL contains project UUID
        assert "text/plain" in put_requests[0]["headers"]["Content-Type"]  # Contains plaintext

        assert "/workspaces/project_" + created_proj_uuid in put_requests[1]["url"]  # check if UUID in called URLs
        assert "application/json" in put_requests[1]["headers"]["Content-Type"]  # Second request is JSON

        project_path = "/projects/{}".format(created_proj_uuid)
        assert len(glob.glob(project_path + "/mainortho/ortho_*.tif")) == 1
        with open(project_path + "/mainortho/indexer.properties") as f:
            assert "PropertyCollectors=TimestampFileNameExtractorSPI[timeregex](ingestion)" in f.read()
        with open(project_path + "/mainortho/timeregex.properties") as f:
            assert f.read() == "regex=[0-9]{8},format=yyyyMMdd"

    def test_compute_disk_space(self, fs, projects: List[UserProject]):
        """
        Tests that the used disk space is updated correctly
        Args:
            fs: The pyfakefs fixture
            projects: A list of projects
        """
        p = projects[0]
        # These should be 41KB and 1MB files, respectively
        fs.create_file(p.get_disk_path() + "/smallfile.txt", contents="A" * 1024 * 41)
        fs.create_file(p.get_disk_path() + "/somewhere/hidden/bigfile.txt", contents="Z" * 1024 * 1024)

        p.update_disk_space()
        p.refresh_from_db()

        assert p.used_space == 1024 + 41


@pytest.mark.django_db
class TestArtifactModel(ProjectsMixin, BaseTestViewSet):
    @staticmethod
    def _test_disk_path(projects, art_type, name, filename, title):
        art = Artifact.objects.create(project=projects[0], type=art_type.name, name=name,
                                      title=title)
        path = art.get_disk_path()
        assert "/projects/" in path
        assert str(projects[0].uuid) in path
        assert name in path
        assert filename in path
        assert title not in path

    def test_disk_path_shapefile(self, projects):
        self._test_disk_path(projects, ArtifactType.SHAPEFILE, "somefile", "poly.shp", "Vector")

    def test_disk_path_index(self, projects):
        self._test_disk_path(projects, ArtifactType.INDEX, "somefile", "somefile.tif", "Index")


@pytest.mark.django_db
class TestFlightModel(FlightsMixin, BaseTestViewSet):
    def test_cannot_repeat_flight_name_on_same_user(self, users):
        u = users[0]
        u.flight_set.create(name="title", date=datetime.now())
        with pytest.raises(IntegrityError):
            u.flight_set.create(name="title", date=datetime.now())

    def test_can_repeat_flight_name_on_different_user(self, users):
        users[0].flight_set.create(name="title", date=datetime.now())
        try:
            users[1].flight_set.create(name="title", date=datetime.now())
        except IntegrityError:
            pytest.fail("Attempt to create flight raised IntegrityError unexpectedly!")

    def test_flight_initializes_as_waiting_for_images(self, users):
        f = users[0].flight_set.create(name="flight", date=datetime.now())
        assert f.state == FlightState.WAITING.name

    def test_flight_png_ortho_path(self, users):
        f = users[0].flight_set.create(name="flight", date=datetime.now())
        assert str(f.uuid) in f.get_png_ortho_path()
        assert f.get_png_ortho_path().endswith("/odm_orthophoto/odm_orthophoto.png")

    def test_get_nodeodm_info(self, users):
        f: Flight = users[0].flight_set.create(name="flight", date=datetime.now())
        f.state = FlightState.PROCESSING.name
        f.save()

        # httpretty.enable()
        httpretty.register_uri(httpretty.GET, "http://container-nodeodm:3000/task/{}/info".format(f.uuid),
                               body=json.dumps({"processingTime": 123, "progress": 42}))
        info = f.get_nodeodm_info()
        assert info["processingTime"] == 123
        assert info["progress"] == 42
        assert info["numImages"] == 0

    def test_compute_disk_space(self, fs, users):
        """
        Tests that the used disk space is updated correctly
        Args:
            fs: The pyfakefs fixture
            users: The User list fixture
        """
        f = users[0].flight_set.create(name="flight", date=datetime.now())
        # These should be 3KB and 3MB files, respectively
        fs.create_file(f.get_disk_path() + "/images.json", contents="A" * 1024 * 3)
        fs.create_file(f.get_disk_path() + "/odm_orthophoto/odm_orthophoto.tif", contents="Z" * 1024 * 1024 * 3)

        f.update_disk_space()
        f.refresh_from_db()

        assert f.used_space == (3 * 1024) + 3


@pytest.mark.django_db
class TestUserModel(FlightsMixin, ProjectsMixin, BaseTestViewSet):
    def test_compute_disk_space(self, fs, users, flights, projects):
        """
        Tests that the used disk space is updated correctly
        Args:
            fs: The pyfakefs fixture
            users: The User list fixture
        """
        u: User = users[0]
        u.refresh_from_db()
        f = u.flight_set.all()[0]
        p = u.user_projects.all()[0]

        # Create files for the user's first Flight
        fs.create_file(f.get_disk_path() + "/smallfile.txt", contents="A" * 1024 * 3)
        fs.create_file(f.get_disk_path() + "/odm_orthophoto/bigfile.tif", contents="Z" * 1024 * 1024 * 3)
        # Create files for the user's first UserProject
        fs.create_file(p.get_disk_path() + "/smallfile.txt", contents="A" * 1024 * 41)
        fs.create_file(p.get_disk_path() + "/somewhere/hidden/bigfile.txt", contents="Z" * 1024 * 1024)

        f.update_disk_space()
        p.update_disk_space()
        u.update_disk_space()  # User.update_disk_space() expects all Flights and Projects to be updated
        u.refresh_from_db()

        assert u.used_space == 3 + (3 * 1024) + 41 + 1024
