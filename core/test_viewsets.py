from datetime import datetime
from typing import List

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from httpretty import httpretty
from rest_framework.test import APIClient

from core.models import Flight, UserProject, Artifact, ArtifactType, Camera, UserType, User


class BaseTestViewSet:
    @pytest.fixture
    def users(self):
        User = get_user_model()
        u1 = User.objects.create(username='temporary', email='temporary@gmail.com', password='temporary')
        u2 = User.objects.create(username='temporary2', email='temporary2@gmail.com', password='temporary2')
        admin = User.objects.create(username='admin', email='admin@gmail.com', password='admin',
                                    type=UserType.ADMIN.name)
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
        f5 = users[2].flight_set.create(name="flight5", date=datetime.now(), camera=Camera.RGB.name)
        return f1, f2, f3, f4, f5

    def setup_class(self):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/init", body="")
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/remove", status=200)

    def teardown_class(self):
        httpretty.disable()


@pytest.mark.django_db
class TestUserViewSet(BaseTestViewSet):
    def test_user_list(self, c, users):
        c.force_authenticate(users[0])
        resp = c.get(reverse('users-list')).json()
        assert any(users[0].email == u["email"] for u in resp)  # Logged in user in response
        assert not any(users[1].email == u["email"] for u in resp)  # Other users NOT in response

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_anonymous_not_allowed(self, c, users):
        c.force_authenticate(user=None)
        assert c.get(reverse('users-list')).status_code == 401

    def test_admin_sees_all(self, c, users):
        c.force_authenticate(users[2])
        resp = c.get(reverse('users-list')).json()
        assert any(users[0].email == u["email"] for u in resp)  # user0 in response
        assert any(users[1].email == u["email"] for u in resp)  # user1 also in response
        assert any(users[2].email == u["email"] for u in resp)  # admin in response

    def test_user_creation(self, c, users):
        resp = c.post(reverse('users-list'),
                      {"email": "foo@example.com", "username": "foo", "password": "foo"})
        assert resp.status_code == 201

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_user_creation_duplicate_email(self, c, users: List[User]):
        resp = c.post(reverse('users-list'),
                      {"email": users[0].email, "username": "foo", "password": "foo"})
        assert resp.status_code == 400
        assert "email" in resp.json()

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_user_creation_wrong_email(self, c, users: List[User]):
        resp = c.post(reverse('users-list'),
                      {"email": "foo@example", "username": "foo", "password": "foo"})
        assert resp.status_code == 400
        assert "email" in resp.json()  # response body is a dict with all failed fields

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_user_creation_no_username(self, c, ):
        resp = c.post(reverse('users-list'),
                      {"email": "foo@example.com", "password": "foo"})
        assert resp.status_code == 400
        assert "username" in resp.json()

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_user_creation_duplicate_username(self, c, users: List[User]):
        resp = c.post(reverse('users-list'),
                      {"email": "foo@example.com", "username": users[0].username, "password": "foo"})
        assert resp.status_code == 400
        assert "username" in resp.json()

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_user_creation_no_password(self, c, users: List[User]):
        resp = c.post(reverse('users-list'),
                      {"email": "foo@example.com", "username": "foo"})
        assert resp.status_code == 400
        assert "password" in resp.json()


@pytest.mark.django_db
class TestFlightViewSet(FlightsMixin, BaseTestViewSet):
    def _test_count_flights(self, c, user, flights, counts):
        c.force_authenticate(user)
        resp = c.get(reverse('flights-list')).json()
        for i in range(len(counts)):
            assert sum(str(flights[i].uuid) == flight['uuid'] for flight in resp) == counts[i]

    def test_flight_list(self, c, users, flights):
        self._test_count_flights(c, users[0], flights, [1, 1, 1, 0, 0])  # user0 sees flights 1, 2 and 3

    def test_admin_sees_only_own_flights_by_default(self, c, users, flights):
        self._test_count_flights(c, users[2], flights, [0, 0, 0, 0, 1])

    def test_admin_can_pose_as_other_user(self, c, users, flights):
        c.force_authenticate(users[2])  # Authenticate as admin, ...
        resp = c.get(reverse('flights-list'),
                     HTTP_TARGETUSER=users[0].pk).json()  # ... request flights, pass special header to simulate user0
        # Flights 1 and 2 should appear on response, but not flights 3 or 4, even though flight4 belongs to admin
        assert str(flights[0].uuid) in (f["uuid"] for f in resp)
        assert str(flights[1].uuid) in (f["uuid"] for f in resp)
        assert str(flights[3].uuid) not in (f["uuid"] for f in resp)
        assert str(flights[4].uuid) not in (f["uuid"] for f in resp)

    def test_admin_can_see_other_flight_details(self, c, users, flights):
        c.force_authenticate(users[2])
        resp = c.get(reverse('flights-detail', kwargs={"pk": flights[0].uuid}),
                     HTTP_TARGETUSER=users[0].pk)
        assert resp.status_code == 200
        assert resp.json()["uuid"] == str(flights[0].uuid)

    def _create_flight(self, c, expected_status, as_user=None):
        kwargs = {"HTTP_TARGETUSER": as_user} if as_user else {}
        resp = c.post(reverse('flights-list'),
                      {"name": "someflight", "date": "2020-01-01", "camera": Camera.REDEDGE.name, "annotations": "foo"},
                      **kwargs)
        assert resp.status_code == expected_status
        return resp

    def test_flight_creation(self, c, users):
        c.force_authenticate(users[1])
        resp = self._create_flight(c, 201)
        assert resp.json()["user"] == users[1].pk

    def test_flight_creation_admin(self, c, users):
        c.force_authenticate(users[2])
        resp = self._create_flight(c, 201)
        assert resp.json()["user"] == users[2].pk

    def test_flight_creation_admin_as_other(self, c, users):
        c.force_authenticate(users[2])  # Login as admin
        resp = self._create_flight(c, 201, users[0].pk)  # create flight as user0
        assert resp.json()["user"] == users[0].pk  # Flight must have been created as property of user0!

    def test_flight_creation_user_as_other(self, c, users):
        c.force_authenticate(users[1])  # login as user0
        resp = self._create_flight(c, 201, users[0].pk)  # try to create flight as user1
        assert resp.json()["user"] == users[1].pk  # Flight must have been created as property of user0!

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_anon_cannot_create_flight(self, c, users):
        c.force_authenticate(user=None)
        self._create_flight(c, 401)

    def test_user_can_delete_own_flight(self, c, users, flights):
        c.force_authenticate(users[0])
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))
        assert resp.status_code == 204

    @pytest.mark.xfail(reason="Weird exception AssertionError: .accepted_renderer not set on Response")
    def test_user_cant_delete_other_flight(self, c, users, flights):
        c.force_authenticate(users[1])
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))
        assert resp.status_code == 404

    def test_admin_can_delete_any_flight(self, c, users, flights):
        c.force_authenticate(users[2])  # Login as admin, try to delete other users flight
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[2].uuid)}), HTTP_TARGETUSER=users[0].pk)
        assert resp.status_code == 204

    def test_soft_delete(self, c, users, flights):
        c.force_authenticate(users[0])
        workspace_url = "http://container-nginx/geoserver/geoserver/rest/workspaces/flight_{}".format(flights[0].uuid)
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
        workspace_url = "http://container-nginx/geoserver/geoserver/rest/workspaces/flight_{}".format(flights[0].uuid)
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

    def test_deleted_list_admin(self, c, users, flights):
        c.force_authenticate(users[2])
        flights[0].deleted = True
        flights[0].save()
        resp = c.get(reverse('flights-deleted'),
                     HTTP_TARGETUSER=users[0].pk).json()  # GET the /api/flights/deleted endpoint masquerading as user0
        assert str(flights[0].uuid) in [f["uuid"] for f in resp]  # flights[0] should be there
        assert str(flights[4].uuid) not in [f["uuid"] for f in resp]  # Admin's own flight should NOT be there


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
        p3 = users[1].user_projects.create(name="proj3")
        p3.flights.add(flights[3])
        return p1, p2, p3

    def setup_class(self):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://container-nginx/geoserver/geoserver/rest/workspaces", "")

    def teardown_class(self):
        httpretty.disable()

    def test_project_list(self, c, users, flights, projects):
        c.force_authenticate(users[0])
        resp = c.get(reverse("projects-list")).json()
        assert sum(str(flights[0].uuid) in proj['flights'] for proj in resp) == 2  # First flight appears 2 times
        assert sum(str(flights[1].uuid) in proj['flights'] for proj in resp) == 1  # Second flight appears 3 times
        assert not any(str(flights[2].uuid) in proj['flights'] for proj in resp)  # Third flight must NOT appear

    def test_other_user_not_allowed(self, c, users):
        c.force_authenticate(users[1])
        assert len(c.get(reverse("projects-list")).json()) == 0

    def test_admin_self_projects(self, c, users):
        c.force_authenticate(users[2])
        assert len(c.get(reverse("projects-list")).json()) == 0

    def test_admin_projects_as_other_user(self, c, users, flights, projects):
        c.force_authenticate(users[2])
        resp = c.get(reverse("projects-list"), HTTP_TARGETUSER=users[1].pk).json()  # M
        assert not any(str(flights[0].uuid) in proj['flights'] for proj in resp)  # First flight must NOT appear
        assert any(str(flights[3].uuid) in proj['flights'] for proj in resp)  # flight3 must appear

    def test_non_admin_projects_as_other_user(self, c, users, flights, projects):
        c.force_authenticate(users[0])  # Login as user0
        resp = c.get(reverse("projects-list"), HTTP_TARGETUSER=users[1].pk).json()  # Try to masquerade as user1
        assert any(str(flights[0].uuid) in proj['flights'] for proj in resp)  # First flight must appear
        assert not any(str(flights[2].uuid) in proj['flights'] for proj in resp)  # Third flight must NOT appear

    def _test_project_creation(self, c, users, flights, monkeypatch, user, proj_flights, as_user=None):
        def fake_create_datastore(*args, **kwargs):
            pass

        monkeypatch.setattr(UserProject, "_create_mainortho_datastore", fake_create_datastore)
        c.force_authenticate(user)
        kwargs = {"HTTP_TARGETUSER": as_user} if as_user else {}
        resp = c.post(reverse('projects-list'),
                      {"flights": proj_flights, "name": "foo", "description": "descr"}, **kwargs)
        assert resp.status_code == 201
        return resp

    def test_project_creation_normal(self, c, users, flights, monkeypatch):
        resp = self._test_project_creation(c, users, flights, monkeypatch, users[0],
                                           [flights[0].uuid, flights[1].uuid]).json()
        assert str(flights[0].uuid) in resp["flights"]
        assert str(flights[1].uuid) in resp["flights"]

    def test_project_creation_admin_as_self(self, c, users, flights, monkeypatch):
        resp = self._test_project_creation(c, users, flights, monkeypatch, users[2], [flights[4].uuid]).json()
        assert str(flights[4].uuid) in resp["flights"]

    def test_project_creation_admin_as_other(self, c, users, flights, monkeypatch):
        resp = self._test_project_creation(c, users, flights, monkeypatch, users[2], [flights[0].uuid, flights[1].uuid],
                                           as_user=users[0].pk).json()
        assert resp["user"] == users[0].pk  # Project should belong to user0
        assert str(flights[0].uuid) in resp["flights"]
        assert str(flights[1].uuid) in resp["flights"]

    def test_project_creation_admin_as_other_mixed_flights(self, c, users, flights, monkeypatch):
        # Try to create a Project as user0 with flights 0 and 4, but flight4 belongs to admin so it shouldn't appear
        resp = self._test_project_creation(c, users, flights, monkeypatch, users[2], [flights[0].uuid, flights[4].uuid],
                                           as_user=users[0].pk).json()
        assert resp["user"] == users[0].pk  # Project should belong to user0
        assert str(flights[0].uuid) in resp["flights"]
        assert str(flights[4].uuid) not in resp["flights"]  # flight4 should NOT be there b/c admin is simulating user0

    def test_project_creation_normal_as_other(self, c, users, flights, monkeypatch):
        # user0 tries to create a Project in the name of user1, it shouldn't work
        resp = self._test_project_creation(c, users, flights, monkeypatch, users[0], [flights[0].pk, flights[3].pk],
                                           as_user=users[1].pk).json()  # Try to pass as user1
        assert resp["user"] == users[0].pk  # Project should belong to user0, not to user1
        assert str(flights[0].uuid) in resp["flights"]
        assert str(flights[3].uuid) not in resp["flights"]  # flight3 should not appear b/c it doesn't belong to user0
