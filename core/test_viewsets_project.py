import re
from typing import List

import pytest
from django.urls import reverse
from httpretty import httpretty

from core.models import UserProject, User, Flight
from core.test_viewsets import FlightsMixin, BaseTestViewSet


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
        p4 = users[2].user_projects.create(name="proj4")
        p4.flights.add(flights[4])
        return p1, p2, p3, p4

    def setup_class(self):
        super().setup_class(self)  # HACK: Required to get the FLightsMixin setup_class code to trigger
        httpretty.enable()
        httpretty.register_uri(httpretty.POST, "http://container-geoserver:8080/geoserver/rest/workspaces", "")

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

    def _test_project_creation(self, c, fs, users, flights, monkeypatch, user, proj_flights, as_user=None):
        httpretty.register_uri(httpretty.PUT,
                               re.compile(
                                   r"http://container-geoserver:8080/geoserver/rest/workspaces/project_.+/coveragestores/mainortho/external.imagemosaic"),
                               status=200)
        httpretty.register_uri(httpretty.PUT,
                               re.compile(
                                   r"http://container-geoserver:8080/geoserver/rest/workspaces/project_.+/coveragestores/mainortho/coverages/mainortho.json"),
                               status=200)
        for f in proj_flights:
            fs.create_file(f"{f.get_disk_path()}/odm_orthophoto/odm_orthophoto.tif", contents="A" * 1024 * 1024)
            fs.create_file(f"{f.get_disk_path()}/odm_orthophoto/rgb.tif", contents="A" * 1024 * 1024)
        c.force_authenticate(user)
        kwargs = {"HTTP_TARGETUSER": as_user} if as_user else {}
        resp = c.post(reverse('projects-list'),
                      {"flights": [f.uuid for f in proj_flights], "name": "foo", "description": "descr"}, **kwargs)
        return resp

    def test_project_creation_normal(self, c, fs, users, flights, monkeypatch):
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[0],
                                           [flights[0], flights[1]])
        assert resp.status_code == 201
        assert str(flights[0].uuid) in resp.json()["flights"]
        assert str(flights[1].uuid) in resp.json()["flights"]

    def test_project_creation_admin_as_self(self, c, fs, users, flights, monkeypatch):
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[2], [flights[4]])
        assert resp.status_code == 201
        assert str(flights[4].uuid) in resp.json()["flights"]

    def test_project_creation_admin_as_other(self, c, fs, users, flights, monkeypatch):
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[2],
                                           [flights[0], flights[1]],
                                           as_user=users[0].pk)
        assert resp.status_code == 201
        assert resp.json()["user"] == users[0].pk  # Project should belong to user0
        assert str(flights[0].uuid) in resp.json()["flights"]
        assert str(flights[1].uuid) in resp.json()["flights"]

    def test_project_creation_over_quota(self, c, fs, monkeypatch, users: List[User], flights: List[Flight]):
        """
        Tests that a User can't create a Project when he is over his disk quota
        Args:
            c: The APIClient fixture
            fs: The pyfakefs fixture
            monkeypatch: The monkeypatching fixture
            users: A fixture containing pre-generated Users
            flights: A fixture containing pre-generated Flights
        """
        users[0].used_space = 50 * 1024 ** 2  # user0 is using 50GB
        users[0].save()
        c.force_authenticate(users[2])  # Login as admin (who is NOT over quota)
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[2],
                                           [flights[0], flights[1]],
                                           as_user=users[0].pk)
        assert resp.status_code == 402
        # project creation should have failed

    def test_project_creation_admin_as_other_mixed_flights(self, c, fs, users, flights, monkeypatch):
        # Try to create a Project as user0 with flights 0 and 4, but flight4 belongs to admin so it shouldn't appear
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[2], [flights[0], flights[4]],
                                           as_user=users[0].pk)
        assert resp.status_code == 201
        assert resp.json()["user"] == users[0].pk  # Project should belong to user0
        assert str(flights[0].uuid) in resp.json()["flights"]
        assert str(flights[4].uuid) not in resp.json()[
            "flights"]  # flight4 should NOT be there b/c admin is simulating user0

    def test_project_creation_normal_as_other(self, c, fs, users, flights, monkeypatch):
        # user0 tries to create a Project in the name of user1, it shouldn't work
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[0], [flights[0], flights[3]],
                                           as_user=users[1].pk)  # Try to pass as user1
        assert resp.status_code == 201
        assert resp.json()["user"] == users[0].pk  # Project should belong to user0, not to user1
        assert str(flights[0].uuid) in resp.json()["flights"]
        # flight3 should not appear b/c it doesn't belong to user0
        assert str(flights[3].uuid) not in resp.json()["flights"]

    def test_user_can_delete_own_project(self, c, users, projects: List[UserProject]):
        c.force_authenticate(users[0])
        resp = c.delete(reverse('projects-detail', kwargs={"pk": str(projects[0].uuid)}))
        assert resp.status_code == 204
        projects[0].refresh_from_db()
        assert projects[0].deleted

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_cant_delete_other_flight(self, c, users, projects: List[UserProject]):
        c.force_authenticate(users[1])
        with pytest.raises(AssertionError):
            c.delete(reverse('projects-detail', kwargs={"pk": str(projects[0].uuid)}))

    def test_admin_can_delete_any_project(self, c, users, projects: List[UserProject]):
        c.force_authenticate(users[2])  # Login as admin, try to delete other user's project
        resp = c.delete(reverse('projects-detail', kwargs={"pk": str(projects[0].uuid)}), HTTP_TARGETUSER=users[0].pk)
        assert resp.status_code == 204
        projects[0].refresh_from_db()
        assert projects[0].deleted

    def test_soft_delete(self, c, fs, users, projects: List[UserProject]):
        c.force_authenticate(users[0])
        workspace_url = "http://container-geoserver:8080/geoserver/rest/workspaces/project_{}".format(projects[0].uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        fs.create_dir(projects[0].get_disk_path())
        c.delete(reverse('projects-detail', kwargs={"pk": str(projects[0].uuid)}))  # Send one DELETE request
        try:
            project = users[0].user_projects.get(uuid=projects[0].uuid)
            assert project.deleted
        except UserProject.DoesNotExist:
            pytest.fail("Project should have existed")
        c.delete(reverse('projects-detail', kwargs={"pk": str(projects[0].uuid)}))  # Repeat the DELETE request
        assert len(users[0].user_projects.filter(uuid=projects[0].uuid)) == 0  # Should not find the Project

    def test_soft_delete_already_deleted(self, c, fs, users, projects: List[UserProject]):
        c.force_authenticate(users[0])
        workspace_url = "http://container-geoserver:8080/geoserver/rest/workspaces/project_{}".format(projects[0].uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        fs.create_dir(projects[0].get_disk_path())
        projects[0].deleted = True  # Manually "delete" the Project
        projects[0].save()
        c.delete(reverse('projects-detail', kwargs={"pk": str(projects[0].uuid)}))  # Issue single DELETE request
        assert len(users[0].user_projects.filter(uuid=projects[0].uuid)) == 0  # Should not find the Project

    def test_deleted_list(self, c, users, projects: List[UserProject]):
        c.force_authenticate(users[0])
        projects[0].deleted = True  # Manually "delete" the Project
        projects[0].save()

        resp = c.get(reverse('projects-list')).json()  # GET the /api/projects endpoint
        assert str(projects[0].uuid) not in [p["uuid"] for p in resp]  # projects[0] should NOT be there
        assert str(projects[1].uuid) in [p["uuid"] for p in resp]  # projects[1] should be there
        resp = c.get(reverse('projects-deleted')).json()  # GET the /api/projects/deleted endpoint
        assert str(projects[0].uuid) in [p["uuid"] for p in resp]  # projects[0] should be there
        assert str(projects[1].uuid) not in [p["uuid"] for p in resp]  # projects[1] should NOT be there

    def test_deleted_list_admin(self, c, users, projects: List[UserProject]):
        c.force_authenticate(users[2])
        projects[0].deleted = True
        projects[0].save()
        resp = c.get(reverse('projects-deleted'),
                     HTTP_TARGETUSER=users[0].pk).json()  # GET the /api/projects/deleted endpoint masquerading as user0
        assert str(projects[0].uuid) in [p["uuid"] for p in resp]  # projects[0] should be there
        assert str(projects[3].uuid) not in [p["uuid"] for p in resp]  # Admin's own project should NOT be there

    def test_project_creation_demo_user(self, c, fs, users, flights, monkeypatch):
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[3], [])
        assert resp.status_code == 403

    def test_project_creation_deleted_user(self, c, fs, users, flights, monkeypatch):
        resp = self._test_project_creation(c, fs, users, flights, monkeypatch, users[4], [])
        assert resp.status_code == 403

    def test_convert_to_demo(self, c, fs, users: List[User], projects: List[UserProject]):
        c.force_authenticate(users[2])  # admin
        assert not projects[3].is_demo
        assert projects[3] not in users[0].demo_projects.all()
        assert users[2].used_space == 0
        fs.create_file(f"{projects[3].get_disk_path()}/whatever.png", contents="A" * 1024 * 20)
        projects[3].update_disk_space()
        projects[3].user.update_disk_space()
        assert users[2].used_space == 20

        resp = c.post(reverse("projects-make-demo",
                              kwargs={"pk": str(projects[3].uuid)}))
        assert resp.status_code == 200
        projects[3].refresh_from_db()
        assert projects[3].is_demo
        assert projects[3].user is None
        assert all([projects[3] in u.demo_projects.all() for u in User.objects.all()])
        assert all([u.used_space == 0 for u in User.objects.all()])

    def test_try_convert_to_demo_nonadmin(self, c, users: List[User], projects: List[UserProject]):
        c.force_authenticate(users[0])  # not admin

        resp = c.post(reverse("projects-make-demo",
                              kwargs={"pk": str(projects[0].uuid)}))
        assert resp.status_code == 403  # only admins can create demos
        projects[0].refresh_from_db()
        assert not projects[0].is_demo
        assert not any([projects[0] in u.demo_projects.all() for u in User.objects.all()])

    def test_list_flight_includes_demo(self, c, fs, users: List[User], projects: List[UserProject]):
        c.force_authenticate(users[0])
        resp = c.get(reverse("projects-list")).json()
        assert str(projects[3].uuid) not in [p["uuid"] for p in resp]

        self.test_convert_to_demo(c, fs, users, projects)  # projects[3] is now a Demo Project
        assert projects[3] in users[0].demo_projects.all()

        c.force_authenticate(users[0])
        resp = c.get(reverse("projects-list")).json()
        assert str(projects[3].uuid) in [p["uuid"] for p in resp]

    def test_delete_demo(self, c, fs, users: List[User], projects: List[UserProject]):
        self.test_convert_to_demo(c, fs, users, projects)  # projects[3] is now a Demo Project

        c.force_authenticate(users[0])
        resp = c.delete(reverse("projects-detail", kwargs={"pk": str(projects[3].uuid)}))
        assert resp.status_code == 204
        projects[3].refresh_from_db()
        assert users[0] not in projects[3].demo_users.all()
        assert users[2] in projects[3].demo_users.all()  # admin is still in project3's demo users
        assert projects[3].is_demo

    def test_delete_demo_admin(self, c, fs, users: List[User], projects: List[UserProject]):
        self.test_convert_to_demo(c, fs, users, projects)  # projects[3] is now a Demo Project

        c.force_authenticate(users[2])
        resp = c.delete(reverse("projects-detail", kwargs={"pk": str(projects[3].uuid)}))
        assert resp.status_code == 204
        projects[3].refresh_from_db()
        assert users[0] in projects[3].demo_users.all()  # normal user still sees project3 as demo
        assert users[2] not in projects[3].demo_users.all()
        assert projects[3].is_demo

    def test_unconvert_demo(self, c, fs, users: List[User], projects: List[UserProject]):
        self.test_convert_to_demo(c, fs, users, projects)  # projects[3] is now a Demo Project
        c.force_authenticate(users[2])
        resp = c.delete(reverse("projects-delete-demo", kwargs={"pk": str(projects[3].uuid)}))
        assert resp.status_code == 204
        projects[3].refresh_from_db()
        assert projects[3].demo_users.count() == 0
        assert not projects[3].is_demo
        assert projects[3].user == users[2]

        users[2].refresh_from_db()
        assert users[2].used_space == 20

    def test_really_delete_demo_nonadmin(self, c, fs, users: List[User], projects: List[UserProject]):
        self.test_convert_to_demo(c, fs, users, projects)  # projects[3] is now a Demo Project

        c.force_authenticate(users[0])
        resp = c.delete(reverse("projects-delete-demo", kwargs={"pk": str(projects[3].uuid)}))
        assert resp.status_code == 403
        projects[3].refresh_from_db()
        assert UserProject.objects.filter(uuid=projects[3].uuid)  # projects[3] was NOT deleted
        assert projects[3].is_demo

    def test_making_demo_project_makes_all_flights_demo(self, c, fs, users: List[User], flights: List[Flight],
                                                        projects: List[UserProject]):
        assert not flights[4].is_demo
        self.test_convert_to_demo(c, fs, users, projects)  # projects[3] is now a Demo Flight
        # projects[3] pulls flights[4] to demo-land

        flights[4].refresh_from_db()
        projects[3].refresh_from_db()
        assert projects[3].is_demo
        assert projects[3].user is None
        assert flights[4].is_demo
        assert flights[4].user is None

    @staticmethod
    def _create_project_with_content(c, fs, users, flights):
        f1 = flights[0]
        f2 = flights[1]
        httpretty.register_uri(httpretty.PUT,
                               re.compile(
                                   r"http://container-geoserver:8080/geoserver/rest/workspaces/project_.+/coveragestores/mainortho/external.imagemosaic"),
                               status=200)
        httpretty.register_uri(httpretty.PUT,
                               re.compile(
                                   r"http://container-geoserver:8080/geoserver/rest/workspaces/project_.+/coveragestores/mainortho/coverages/mainortho.json"),
                               status=200)
        for f in (f1, f2):
            fs.create_file(f"{f.get_disk_path()}/odm_orthophoto/odm_orthophoto.tif", contents="A" * 1024 * 1024)
            fs.create_file(f"{f.get_disk_path()}/odm_orthophoto/rgb.tif", contents="A" * 1024 * 1024)
            f.update_disk_space()
        c.force_authenticate(users[0])
        assert users[0].used_space == 0
        resp = c.post(reverse('projects-list'),
                      {"flights": [f1.uuid, f2.uuid], "name": "foo", "description": "descr"})
        return resp

    def test_project_creation_disk_space(self, c, fs, users: List[User], flights: List[Flight],
                                         projects: List[UserProject]):
        resp = self._create_project_with_content(c, fs, users, flights)
        assert resp.status_code == 201
        data = resp.json()
        p = UserProject.objects.get(uuid=data["uuid"])
        assert p.used_space == 2048  # 2 orthomosaics, each takes 1MB
        assert users[0].used_space == 6 * 1024  # 2 flights of 2MB each (2 orthos, 1MB each) and the project takes 2MB

    def test_project_deletion_disk_space(self, c, fs, users: List[User], flights: List[Flight],
                                         projects: List[UserProject]):
        resp = self._create_project_with_content(c, fs, users, flights)
        data = resp.json()
        p = UserProject.objects.get(uuid=data["uuid"])
        users[0].refresh_from_db()
        prev_space = users[0].used_space
        assert prev_space != 0

        workspace_url = "http://container-geoserver:8080/geoserver/rest/workspaces/project_{}".format(p.uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        p.deleted = True
        p.save()
        c.delete(reverse('projects-detail', kwargs={"pk": str(p.uuid)}))  # Issue single DELETE request

        users[0].refresh_from_db()
        assert users[0].used_space < prev_space  # not 0 because there are leftover FLights and Projects
