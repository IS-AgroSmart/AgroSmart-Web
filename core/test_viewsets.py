import re
from datetime import datetime, timedelta
from typing import List

import pytest
from django.urls import reverse
from httpretty import httpretty
from rest_framework.test import APIClient

from core.models import Artifact, ArtifactType, Camera, UserType, User, FlightState, BlockCriteria


class BaseTestViewSet:
    @pytest.fixture
    def users(self, fs):
        from pyfakefs.fake_filesystem_unittest import Pause
        with Pause(fs):
            # Pause(fs) stops the fake filesystem and allows Django access to the common password list
            u1 = User.objects.create_user(username='temporary', email='temporary@gmail.com', password='temporary',
                                          type=UserType.ACTIVE.name)
            u2 = User.objects.create_user(username='temporary2', email='temporary2@gmail.com', password='temporary2',
                                          type=UserType.ACTIVE.name)
            admin = User.objects.create_user(username='admin', email='admin@gmail.com', password='admin',
                                             type=UserType.ADMIN.name)
            demo = User.objects.create_user(username='demo', email='demo@gmail.com', password='demo',
                                            type=UserType.DEMO_USER.name)
            deleted = User.objects.create_user(username='deleted', email='deleted@gmail.com', password='deleted',
                                               type=UserType.DELETED.name, is_active=False)
        return u1, u2, admin, demo, deleted

    @pytest.fixture
    def c(self):
        return APIClient()


class FlightsMixin:
    """Add to test classes that need access to Flights

    Automatically activates API mocking for the NodeODM endpoint

    Exposed fixtures:
        flights (([User]) -> [Flight]): Pytest fixture, returns four Flights
    """

    @pytest.fixture
    def flights(self, users):
        f1 = users[0].flight_set.create(name="flight1", date=datetime.now())
        f2 = users[0].flight_set.create(name="flight2", date=datetime.now() - timedelta(days=2))
        f3 = users[0].flight_set.create(name="flight3", date=datetime.now())
        f4 = users[1].flight_set.create(name="flight4", date=datetime.now())
        f5 = users[2].flight_set.create(name="flight5", date=datetime.now(), state=FlightState.COMPLETE.name)
        for f in [f1, f2]:
            f.camera = Camera.REDEDGE.name
            f.save()
        return f1, f2, f3, f4, f5

    def setup_class(self):
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/init", body="")
        httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/remove", status=200)
        httpretty.register_uri(httpretty.POST, re.compile(r"http://container-webhook-adapter:8080/register/.+"),
                               status=200)

    def teardown_class(self):
        httpretty.disable()


@pytest.mark.django_db
class TestUserViewSet(FlightsMixin, BaseTestViewSet):
    def test_user_list(self, c, users):
        c.force_authenticate(users[0])
        resp = c.get(reverse('users-list')).json()
        assert any(users[0].email == u["email"] for u in resp)  # Logged in user in response
        assert not any(users[1].email == u["email"] for u in resp)  # Other users NOT in response

    def test_user_details_contain_disk_info(self, c, users: List[User]):
        """
        Tests that the user detail JSON contains disk quota info (maximum allowed space & currently used space)
        Args:
            c: The APIClient fixture
            users: A fixture containing pre-generated Users
        """
        users[0].used_space = 20000  # approx. 20MB
        users[0].save()
        c.force_authenticate(users[0])
        resp = c.get(reverse('users-detail', kwargs={"pk": users[0].pk})).json()

        assert resp.get("used_space") == 20000
        assert resp.get("maximum_space") == 45 * 1024 ** 2

    @pytest.mark.xfail(reason="Returns 401, which raises an AssertionError due to some bug (?)")
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
                      {"email": "foo@example.com", "username": "foo", "password": "foo", "organization": "org",
                       "first_name": "My Real Name"})
        assert resp.status_code == 201

    def test_user_change_password_self(self, c, users: List[User]):
        c.force_authenticate(users[0])
        oldpass = users[0].password
        resp = c.post(reverse('users-set-password', kwargs={"pk": users[0].pk}), {"password": "mynewpassword"})
        assert resp.status_code == 200
        users[0].refresh_from_db()
        assert users[0].password != oldpass  # can't directly compare passwords because hashes!

    @pytest.mark.xfail(reason="Returns 401, which raises an AssertionError due to some bug (?)")
    def test_user_change_password_other(self, c, users: List[User]):
        c.force_authenticate(users[1])
        oldpass = users[0].password
        resp = c.post(reverse('users-set-password', kwargs={"pk": users[0].pk}), {"password": "mynewpassword"})
        assert resp.status_code == 404
        users[0].refresh_from_db()
        assert users[0].password == oldpass

    def test_user_change_password_admin(self, c, users: List[User]):
        c.force_authenticate(users[2])  # users[2] is admin
        oldpass = users[0].password
        resp = c.post(reverse('users-set-password', kwargs={"pk": users[0].pk}), {"password": "mynewpassword"})
        assert resp.status_code == 200
        users[0].refresh_from_db()
        assert users[0].password != oldpass

    @pytest.mark.xfail(reason="Returns 401, which raises an AssertionError due to some bug (?)")
    def test_user_creation_duplicate_email(self, c, users: List[User]):
        resp = c.post(reverse('users-list'), {"email": users[0].email, "username": "foo", "password": "foo"})
        assert resp.status_code == 400

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_creation_wrong_email(self, c, users: List[User]):
        with pytest.raises(AssertionError):
            c.post(reverse('users-list'), {"email": "foo@example", "username": "foo", "password": "foo"})

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_creation_no_username(self, c, ):
        with pytest.raises(AssertionError):
            c.post(reverse('users-list'),
                   {"email": "foo@example.com", "password": "foo"})

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_creation_duplicate_username(self, c, users: List[User]):
        with pytest.raises(AssertionError):
            c.post(reverse('users-list'),
                   {"email": "foo@example.com", "username": users[0].username, "password": "foo"})

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_creation_no_password(self, c, users: List[User]):
        with pytest.raises(AssertionError):
            c.post(reverse('users-list'),
                   {"email": "foo@example.com", "username": "foo"})

    def test_user_login_correct_password(self, c, users: List[User]):
        resp = c.post(reverse('api_auth'), {"username": "temporary", "password": "temporary"})
        assert resp.status_code == 200
        assert "token" in resp.json()

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_login_wrong_password(self, c, users: List[User]):
        with pytest.raises(AssertionError):
            c.post(reverse('api_auth'), {"username": "temporary", "password": "wrongpass"})

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_login_deleted_user_fails(self, c, users: List[User]):
        deleted = User.objects.create_user(username='deletednew', email='deletednew@gmail.com', password='deletednew')

        # Test successful login, just to be sure
        resp = c.post(reverse('api_auth'), {"username": "deletednew", "password": "deletednew"})
        assert resp.status_code == 200
        assert "token" in resp.json()

        # Mark user as deleted
        deleted.type = UserType.DELETED.name
        deleted.is_active = False
        deleted.save()
        deleted.refresh_from_db()

        # Try to log in again, should NOT work
        with pytest.raises(AssertionError):
            c.post(reverse('api_auth'), {"username": "deletednew", "password": "deletednew"})

    @staticmethod
    def _test_user_delete_as(c, as_user, target_user):
        c.force_authenticate(as_user)
        resp = c.delete(reverse('users-detail', kwargs={"pk": target_user.pk}))
        assert resp.status_code == 204
        target_user.refresh_from_db()
        assert target_user.type == UserType.DELETED.name
        assert not target_user.is_active

    def test_user_delete_self(self, c, users: List[User]):
        self._test_user_delete_as(c, as_user=users[0], target_user=users[0])

    def test_user_delete_self_twice(self, c, users: List[User]):
        self.test_user_delete_self(c, users)  # At this point user is soft-deleted
        resp = c.delete(reverse('users-detail', kwargs={"pk": users[0].pk}))
        assert resp.status_code == 204
        assert len(User.objects.filter(username=users[0].username).all()) == 0

    def test_user_admin_delete_other(self, c, users: List[User]):
        self._test_user_delete_as(c, as_user=users[2], target_user=users[0])  # users[2] is admin

    def test_new_user_gets_demo_flights(self, c, users, flights):
        # create a demo Flight
        c.force_authenticate(users[2])  # admin
        resp = c.post(reverse("flights-make-demo",
                              kwargs={"pk": str(flights[4].uuid)}))
        assert resp.status_code == 200

        # test_user_creation creates user with email foo@example.com
        self.test_user_creation(c, users)
        new_user = User.objects.get(email="foo@example.com")
        new_user.refresh_from_db()
        assert flights[4] in new_user.demo_flights.all()

    def test_new_user_gets_demo_projects(self, c, users, flights):
        # create a demo Project
        c.force_authenticate(users[2])  # admin
        p = users[2].user_projects.create(name="proj1")
        p.flights.add(flights[4])
        resp = c.post(reverse("projects-make-demo",
                              kwargs={"pk": str(p.uuid)}))
        assert resp.status_code == 200

        # test_user_creation creates user with email foo@example.com
        self.test_user_creation(c, users)
        new_user = User.objects.get(email="foo@example.com")
        new_user.refresh_from_db()
        assert p in new_user.demo_projects.all()


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
class TestBlockCriteriaViewSet(BaseTestViewSet):
    @pytest.fixture
    def block_criteria(self):
        art1 = BlockCriteria.objects.create(type="Ip", ip='127.0.0.8', value=None)
        art2 = BlockCriteria.objects.create(type="Domain", value="fake.com")
        return art1, art2

    def test_create_criteria(self, c, users, block_criteria):
        c.force_authenticate(users[0])
        resp = c.get(reverse('block_criteria-list')).json()
        assert any(a["type"] == block_criteria[0].type and a["ip"] == block_criteria[0].ip for a in resp)
        assert any(a["type"] == block_criteria[1].type and a["value"] == block_criteria[1].value for a in resp)
