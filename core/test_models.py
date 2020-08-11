import glob
import signal
from datetime import datetime
from typing import List
import os
import requests
from django.db.models.signals import post_save, post_delete
import json

import pytest
from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from httpretty import httpretty
from rest_framework.test import APIClient

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
            nonlocal create_ws_executed
            create_ws_executed = True
            return [200, response_headers, ""]

        def mock_requests_put(*args, **kwargs):
            nonlocal put_requests
            put_requests.append({"url": args[0], "headers": kwargs["headers"], "data": kwargs["data"]})

        httpretty.register_uri(httpretty.POST, "http://container-nginx/geoserver/geoserver/rest/workspaces",
                               mark_create_ws_executed)
        import inspect, django, pytz
        fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
        fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
        fs.create_file("/flights/{}/odm_orthophoto/odm_orthophoto.tif".format(flights[2].uuid), contents="")
        monkeypatch.setattr(requests, "put", mock_requests_put)

        resp = c.post(reverse('projects-list'), {"name": "foo", "description": "bar", "flights": flights[2].uuid})
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


@pytest.mark.django_db
class TestArtifactModel(ProjectsMixin, BaseTestViewSet):
    def _test_disk_path(self, projects, type, name, filename, title):
        art = Artifact.objects.create(project=projects[0], type=type.name, name=name,
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


class FlightModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('temporary', 'temporary@gmail.com', 'temporary')
        self.user2 = User.objects.create_user('temporary2', 'temporary2@gmail.com', 'temporary')

        post_save.disconnect(create_nodeodm_task, sender=Flight)
        post_save.disconnect(link_demo_flight_to_active_users, sender=Flight)
        post_delete.disconnect(delete_nodeodm_task, sender=Flight)
        post_delete.disconnect(delete_thumbnail, sender=Flight)
        post_delete.disconnect(delete_geoserver_workspace, sender=Flight)
        post_delete.disconnect(delete_geoserver_workspace, sender=UserProject)
        post_delete.disconnect(delete_on_disk, sender=UserProject)

    def test_cannot_repeat_flight_name_on_same_user(self):
        self.user.flight_set.create(name="title", date=datetime.now())
        self.assertRaises(IntegrityError, self.user.flight_set.create, name="title", date=datetime.now())

    def test_can_repeat_flight_name_on_different_user(self):
        self.user.flight_set.create(name="title", date=datetime.now())
        try:
            self.user2.flight_set.create(name="title", date=datetime.now())
        except IntegrityError:
            self.fail("Attempt to create flight raised IntegrityError unexpectedly!")

    def test_flight_initializes_as_waiting_for_images(self):
        f = self.user.flight_set.create(name="flight", date=datetime.now())
        self.assertEqual(f.state, FlightState.WAITING.name)

    def test_flight_png_ortho_path(self):
        f = self.user.flight_set.create(name="flight", date=datetime.now())
        self.assertTrue(str(f.uuid) in f.get_png_ortho_path())
        self.assertTrue(f.get_png_ortho_path().endswith("/odm_orthophoto/odm_orthophoto.png"))

    def test_get_nodeodm_info(self):
        f: Flight = self.user.flight_set.create(name="flight", date=datetime.now())
        f.state = FlightState.PROCESSING.name
        f.save()

        httpretty.enable()
        httpretty.register_uri(httpretty.GET, "http://container-nodeodm:3000/task/{}/info".format(f.uuid),
                               body=json.dumps({"processingTime": 123, "progress": 42}))
        info = f.get_nodeodm_info()
        assert info["processingTime"] == 123
        assert info["progress"] == 42
        assert info["numImages"] == 0
