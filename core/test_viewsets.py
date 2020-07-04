from datetime import datetime
from typing import List

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from httpretty import httpretty
from rest_framework.test import APIClient

from core.models import Flight, UserProject, Artifact, ArtifactType, Camera


class BaseTestViewSet:
    @pytest.fixture
    def users(self):
        User = get_user_model()
        u1 = User.objects.create(username='temporary', email='temporary@gmail.com', password='temporary')
        u2 = User.objects.create(username='temporary2', email='temporary2@gmail.com', password='temporary2')
        admin = User.objects.create(username='admin', email='admin@gmail.com', password='admin', is_staff=True)
        return u1, u2, admin

    @pytest.fixture
    def c(self):
        return APIClient()


class FlightsMixin:
    """Add to test classes that need access to Flights

    Automatically activates API mocking for the NodeODM endpoint

    Attributes:
        flights (([User]) -> [Flight]): Pytest fixture, returns four Flights

    """

    @pytest.fixture
    def flights(self, users):
        f1 = users[0].flight_set.create(name="flight1", date=datetime.now(), camera=Camera.REDEDGE.name)
        f2 = users[0].flight_set.create(name="flight2", date=datetime.now(), camera=Camera.REDEDGE.name)
        f3 = users[0].flight_set.create(name="flight3", date=datetime.now(), camera=Camera.RGB.name)
        f4 = users[1].flight_set.create(name="flight4", date=datetime.now(), camera=Camera.RGB.name)
        return f1, f2, f3, f4

    def setup_class(self):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/init", body="")
        httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/remove", status=200)

    def teardown_class(self):
        httpretty.disable()


@pytest.mark.django_db
class TestUserViewSet(BaseTestViewSet):
    def test_user_list(self, c, users):
        c.force_authenticate(users[0])
        resp = c.get(reverse('users-list')).json()
        assert any(users[0].email == u["email"] for u in resp)  # Logged in user in response
        assert not any(users[1].email == u["email"] for u in resp)  # Other users NOT in response

    @pytest.mark.xfail
    def test_anonymous_not_allowed(self, c, users):
        assert c.get(reverse('users-list')).status_code == 401


@pytest.mark.django_db
class TestFlightViewSet(FlightsMixin, BaseTestViewSet):
    def _test_count_flights(self, c, user, flights, counts):
        c.force_authenticate(user)
        resp = c.get(reverse('flights-list')).json()
        for i in range(len(counts)):
            assert sum(str(flights[i].uuid) == flight['uuid'] for flight in resp) == counts[i]

    def test_flight_list(self, c, users, flights):
        self._test_count_flights(c, users[0], flights, [1, 1, 1, 0])  # user0 sees flights 1, 2 and 3

    def test_admin_sees_all_flights(self, c, users, flights):
        self._test_count_flights(c, users[2], flights, [1, 1, 1, 1])

    def _create_flight(self, c, expected_status):
        resp = c.post(reverse('flights-list'),
                      {"name": "someflight", "date": "2020-01-01", "camera": Camera.REDEDGE.name, "annotations": "foo"})
        assert resp.status_code == expected_status
        return resp

    def test_flight_creation(self, c, users):
        c.force_authenticate(users[1])
        resp = self._create_flight(c, 201)
        assert resp.json()["user"] == users[1].pk

    @pytest.mark.xfail
    def test_anon_cannot_create_flight(self, c, users):
        self._create_flight(c, 401)

    def test_user_can_delete_own_flight(self, c, users, flights):
        c.force_authenticate(users[0])
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))
        assert resp.status_code == 204

    @pytest.mark.xfail
    def test_user_cant_delete_other_flight(self, c, users, flights):
        c.force_authenticate(users[1])
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))
        assert resp.status_code == 404

    @pytest.mark.xfail(reason="limitation of force_authenticate???")
    def test_admin_can_delete_any_flight(self, c, users, flights):
        c.force_authenticate(users[1])
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=users[0])
        c.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[2].uuid)}))
        assert resp.status_code == 204

    def test_soft_delete(self, c, users, flights):
        c.force_authenticate(users[0])
        workspace_url = "http://localhost/geoserver/geoserver/rest/workspaces/flight_{}".format(flights[0].uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))  # Send one DELETE request
        try:
            flight = users[0].flight_set.get(uuid=flights[0].uuid)
            assert flight.deleted
        except Flight.DoesNotExist:
            pytest.fail("Flight should have existed")
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))  # Repeat the DELETE request
        print(resp.status_code)
        assert len(users[0].flight_set.filter(uuid=flights[0].uuid)) == 0  # Should not find the Flight

    def test_soft_delete_already_deleted(self, c, users, flights):
        c.force_authenticate(users[0])
        workspace_url = "http://localhost/geoserver/geoserver/rest/workspaces/flight_{}".format(flights[0].uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        flights[0].deleted = True  # Manually "delete" the Flight
        flights[0].save()
        c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))  # Issue single DELETE request
        assert len(users[0].flight_set.filter(uuid=flights[0].uuid)) == 0  # Should not find the Flight

    def test_deleted_list(self, c, users, flights):
        c.force_authenticate(users[0])
        flights[0].deleted = True  # Manually "delete" the Flight
        flights[0].save()

        resp = c.get(reverse('flights-list')).json()  # GET the /api/flights endpoint
        assert str(flights[0].uuid) not in [f["uuid"] for f in resp]  # flights[0] should NOT be there
        assert str(flights[1].uuid) in [f["uuid"] for f in resp]  # flights[1] should be there
        resp = c.get(reverse('flights-deleted')).json()  # GET the /api/flights/deleted endpoint
        assert str(flights[0].uuid) in [f["uuid"] for f in resp]  # flights[0] should be there
        assert str(flights[1].uuid) not in [f["uuid"] for f in resp]  # flights[1] should NOT be there


@pytest.mark.django_db
class TestArtifactViewSet(BaseTestViewSet):
    @pytest.fixture
    def artifacts(self):
        art1 = Artifact.objects.create(name="art1", type=ArtifactType.SHAPEFILE.name)
        art2 = Artifact.objects.create(name="art2", type=ArtifactType.INDEX.name)
        return art1, art2

    def test_artifact_list(self, c, users, artifacts):
        c.force_authenticate(users[0])
        resp = c.get(reverse('artifacts-list')).json()
        assert any(a["name"] == artifacts[0].name and a["type"] == artifacts[0].type for a in resp)
        assert any(a["name"] == artifacts[1].name and a["type"] == artifacts[1].type for a in resp)


@pytest.mark.django_db
class TestUserProjectViewSet(FlightsMixin, BaseTestViewSet):
    @pytest.fixture
    def projects(self, users, flights):
        p1 = users[0].user_projects.create(name="proj1")
        p1.flights.add(flights[0], flights[1])
        p2 = users[0].user_projects.create(name="proj2")
        p2.flights.add(flights[0])
        return p1, p2

    def setup_class(self):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://localhost/geoserver/geoserver/rest/workspaces", "")

    def teardown_class(self):
        httpretty.disable()

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

    def test_project_creation(self, c, users, flights, monkeypatch):
        def fake_create_datastore(*args, **kwargs):
            pass

        monkeypatch.setattr(UserProject, "_create_mainortho_datastore", fake_create_datastore)
        c.force_authenticate(users[0])
        resp = c.post(reverse('projects-list'),
                      {"flights": [flights[0].pk, flights[1].pk], "name": "foo", "description": "descr"})
        print(resp.content)
        assert resp.status_code == 201
