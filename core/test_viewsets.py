from datetime import datetime
from typing import List

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from httpretty import httpretty
from rest_framework.test import APIClient

from core.models import Flight, UserProject, Artifact, ArtifactType


class BaseTestViewSet:
    @pytest.fixture
    def users(self):
        User = get_user_model()
        u1 = User.objects.create(username='temporary', email='temporary@gmail.com', password='temporary')
        u2 = User.objects.create(username='temporary2', email='temporary2@gmail.com', password='temporary2')
        return u1, u2

    @pytest.fixture
    def flights(self, users):
        users[0].flight_set.create(name="flight1", date=datetime.now())
        users[0].flight_set.create(name="flight2", date=datetime.now())
        users[0].flight_set.create(name="flight3", date=datetime.now())
        return users[0].flight_set.all()

    @pytest.fixture
    def c(self):
        return APIClient()


@pytest.mark.django_db
class TestUserViewSet(BaseTestViewSet):
    def test_user_list(self, c, users):
        c.force_authenticate(users[0])
        resp = c.get(reverse('users-list')).json()
        assert any(users[0].email == u["email"] for u in resp)  # Logged in user in response
        assert not any(users[1].email == u["email"] for u in resp)  # Other users NOT in response

    def test_anonymous_not_allowed(self, c, users):
        assert c.get(reverse('users-list')).status_code == 401


@pytest.mark.django_db
class TestArtifactViewSet(BaseTestViewSet):
    @pytest.fixture
    def artifacts(self):
        art1 = Artifact.objects.create(name="art1", type=ArtifactType.SHAPEFILE.name)
        art2 = Artifact.objects.create(name="art2", type=ArtifactType.INDEX.name)
        return art1, art2

    def setup_method(self):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/init", body="")

    def test_artifact_list(self, c, users, artifacts):
        c.force_authenticate(users[0])
        resp = c.get(reverse('artifacts-list')).json()
        assert any(a["name"] == artifacts[0].name and a["type"] == artifacts[0].type for a in resp)
        assert any(a["name"] == artifacts[1].name and a["type"] == artifacts[1].type for a in resp)

    def teardown_module(self):
        httpretty.disable()


@pytest.mark.django_db
class TestUserProjectViewSet(BaseTestViewSet):
    @pytest.fixture
    def projects(self, users, flights):
        p1 = users[0].user_projects.create(name="proj1")
        p1.flights.add(flights[0], flights[1])
        p2 = users[0].user_projects.create(name="proj2")
        p2.flights.add(flights[0])
        return p1, p2

    def test_project_list(self, c, users, flights, projects):
        c.force_authenticate(users[0])
        resp = c.get(reverse("projects-list")).json()
        print(resp)
        assert sum(str(flights[0].uuid) in proj['flights'] for proj in resp) == 2  # First flight appears 2 times
        assert sum(str(flights[1].uuid) in proj['flights'] for proj in resp) == 1  # Second flight appears 3 times
        assert not any(str(flights[2].uuid) in proj['flights'] for proj in resp)  # Third flight must NOT appear

    def test_other_user_not_allowed(self, c, users):
        c.force_authenticate(users[1])
        assert len(c.get(reverse("projects-list")).json()) == 0
