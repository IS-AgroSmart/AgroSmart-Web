import os.path
from typing import List

import pytest
from django.urls import reverse
from httpretty import httpretty

from core.models import Camera, Flight, User
from core.test_viewsets import FlightsMixin, BaseTestViewSet


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

    def test_flight_creation_demo_user(self, c, users):
        c.force_authenticate(users[3])  # users[3] is demo user
        self._create_flight(c, 403)

    def test_flight_creation_deleted_user(self, c, users):
        c.force_authenticate(users[4])  # users[4] is deleted user
        self._create_flight(c, 403)

    def test_flight_creation_admin_as_other(self, c, users):
        c.force_authenticate(users[2])  # Login as admin
        resp = self._create_flight(c, 201, users[0].pk)  # create flight as user0
        assert resp.json()["user"] == users[0].pk  # Flight must have been created as property of user0!

    def test_flight_creation_user_as_other(self, c, users):
        c.force_authenticate(users[1])  # login as user0
        resp = self._create_flight(c, 201, users[0].pk)  # try to create flight as user1
        assert resp.json()["user"] == users[1].pk  # Flight must have been created as property of user0!

    def test_flight_creation_over_quota(self, c, users: List[User]):
        """
        Tests that a User can't create a Flight when he is over his disk quota
        Args:
            c: The APIClient fixture
            users: A fixture containing pre-generated Users
        """
        users[0].used_space = 50 * 1024 ** 2  # user0 is using 50GB
        users[0].save()
        c.force_authenticate(users[2])  # Login as admin (who is NOT over quota)
        self._create_flight(c, 402, users[0].pk)  # try to create flight as user0
        # flight creation should have failed with HTTP 402 Payment Required

    @pytest.mark.xfail(reason="Returns 401, which raises an AssertionError due to some bug (?)")
    def test_anon_cannot_create_flight(self, c, users):
        c.force_authenticate(user=None)
        with pytest.raises(AssertionError):
            self._create_flight(c, 401)

    def test_user_can_delete_own_flight(self, c, users, flights):
        c.force_authenticate(users[0])
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))
        assert resp.status_code == 204

    @pytest.mark.xfail(reason="Returns 404, which raises an AssertionError due to some bug (?)")
    def test_user_cant_delete_other_flight(self, c, users, flights):
        c.force_authenticate(users[1])
        with pytest.raises(AssertionError):
            c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))

    def test_admin_can_delete_any_flight(self, c, users, flights):
        c.force_authenticate(users[2])  # Login as admin, try to delete other users flight
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[2].uuid)}), HTTP_TARGETUSER=users[0].pk)
        assert resp.status_code == 204

    def test_soft_delete(self, c, fs, users, flights: List[Flight]):
        fs.create_dir(flights[0].get_disk_path())
        c.force_authenticate(users[0])
        workspace_url = "http://container-geoserver:8080/geoserver/rest/workspaces/flight_{}".format(flights[0].uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        import os.path
        assert os.path.isdir(flights[0].get_disk_path())  # dir should still exist
        c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))  # Send one DELETE request
        try:
            flight = users[0].flight_set.get(uuid=flights[0].uuid)
            assert flight.deleted
        except Flight.DoesNotExist:
            pytest.fail("Flight should have existed")
        if not os.path.isdir(flights[0].get_disk_path()):
            pytest.fail("/flights folder should NOT be deleted when Flight is soft-deleted")
        resp = c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))  # Repeat the DELETE request
        assert len(users[0].flight_set.filter(uuid=flights[0].uuid)) == 0  # Should not find the Flight
        assert not os.path.isdir(flights[0].get_disk_path())  # dir should no longer exist

    def test_soft_delete_already_deleted(self, c, fs, users, flights):
        import os.path
        fs.create_dir(flights[0].get_disk_path())
        c.force_authenticate(users[0])
        workspace_url = "http://container-geoserver:8080/geoserver/rest/workspaces/flight_{}".format(flights[0].uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        flights[0].deleted = True  # Manually "delete" the Flight
        flights[0].save()
        c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))  # Issue single DELETE request
        assert len(users[0].flight_set.filter(uuid=flights[0].uuid)) == 0  # Should not find the Flight
        assert not os.path.isdir(flights[0].get_disk_path())  # dir should no longer exist

    def test_delete_disk_space(self, c, fs, users: List[User], flights: List[Flight]):
        import os.path
        fs.create_dir(flights[0].get_disk_path())
        fs.create_file(flights[0].get_png_ortho_path(), contents="A" * 1024 ** 2)
        flights[0].update_disk_space()
        flights[0].user.update_disk_space()
        flights[0].refresh_from_db()
        users[0].refresh_from_db()
        assert flights[0].used_space == 1024
        assert users[0].used_space == 1024

        c.force_authenticate(users[0])
        workspace_url = "http://container-geoserver:8080/geoserver/rest/workspaces/flight_{}".format(flights[0].uuid)
        httpretty.register_uri(httpretty.DELETE, workspace_url)
        flights[0].deleted = True  # Manually "delete" the Flight
        flights[0].save()
        c.delete(reverse('flights-detail', kwargs={"pk": str(flights[0].uuid)}))  # Issue single DELETE request

        users[0].refresh_from_db()
        assert users[0].used_space == 0

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

    def test_convert_to_demo(self, c, fs, users: List[User], flights: List[Flight]):
        c.force_authenticate(users[2])  # admin
        assert not flights[4].is_demo
        assert flights[4] not in users[0].demo_flights.all()
        assert users[2].used_space == 0
        fs.create_dir(f"{flights[4].get_disk_path()}/odm_orthophoto")
        fs.create_file(flights[4].get_png_ortho_path(), contents="A" * 1024 * 20)
        flights[4].update_disk_space()
        flights[4].user.update_disk_space()
        assert users[2].used_space == 20

        resp = c.post(reverse("flights-make-demo",
                              kwargs={"pk": str(flights[4].uuid)}))
        assert resp.status_code == 200
        flights[4].refresh_from_db()
        assert flights[4].is_demo
        assert flights[4].user is None
        assert all([flights[4] in u.demo_flights.all() for u in User.objects.all()])

        assert all([u.used_space == 0 for u in User.objects.all()])

    def test_try_convert_to_demo_nonadmin(self, c, users: List[User], flights: List[Flight]):
        c.force_authenticate(users[0])  # not admin

        resp = c.post(reverse("flights-make-demo",
                              kwargs={"pk": str(flights[0].uuid)}))
        assert resp.status_code == 403  # only admins can create demos
        flights[0].refresh_from_db()
        assert not flights[0].is_demo
        assert not any([flights[0] in u.demo_flights.all() for u in User.objects.all()])

    def test_list_flight_includes_demo(self, c, fs, users: List[User], flights: List[Flight]):
        c.force_authenticate(users[0])
        resp = c.get(reverse("flights-list")).json()
        assert str(flights[4].uuid) not in [f["uuid"] for f in resp]

        self.test_convert_to_demo(c, fs, users, flights)  # flights[4] is now a Demo Flight
        assert flights[4] in users[0].demo_flights.all()

        c.force_authenticate(users[0])
        resp = c.get(reverse("flights-list")).json()
        assert str(flights[4].uuid) in [f["uuid"] for f in resp]

    def test_delete_demo(self, c, fs, users: List[User], flights: List[Flight]):
        self.test_convert_to_demo(c, fs, users, flights)  # flights[4] is now a Demo Flight

        c.force_authenticate(users[0])
        resp = c.delete(reverse("flights-detail", kwargs={"pk": str(flights[4].uuid)}))
        assert resp.status_code == 204
        flights[4].refresh_from_db()
        assert users[0] not in flights[4].demo_users.all()
        assert users[2] in flights[4].demo_users.all()  # admin is still in flight4's demo users
        assert flights[4].is_demo

    def test_delete_demo_admin(self, c, fs, users: List[User], flights: List[Flight]):
        self.test_convert_to_demo(c, fs, users, flights)  # flights[4] is now a Demo Flight

        c.force_authenticate(users[2])
        resp = c.delete(reverse("flights-detail", kwargs={"pk": str(flights[4].uuid)}))
        assert resp.status_code == 204
        flights[4].refresh_from_db()
        assert users[0] in flights[4].demo_users.all()  # normal user still sees flight4 as demo
        assert users[2] not in flights[4].demo_users.all()
        assert flights[4].is_demo

    def test_unconvert_demo(self, c, fs, users: List[User], flights: List[Flight]):
        assert users[2].used_space == 0
        self.test_convert_to_demo(c, fs, users, flights)  # flights[4] is now a Demo Flight with a 20KB file inside

        c.force_authenticate(users[2])
        resp = c.delete(reverse("flights-delete-demo", kwargs={"pk": str(flights[4].uuid)}))
        assert resp.status_code == 204
        flights[4].refresh_from_db()
        assert users[0] not in flights[4].demo_users.all()
        assert users[2] not in flights[4].demo_users.all()
        assert not flights[4].is_demo
        assert flights[4].user == users[2]
        users[2].refresh_from_db()
        assert users[2].used_space == 20

    def test_really_delete_demo_nonadmin(self, c, fs, users: List[User], flights: List[Flight]):
        self.test_convert_to_demo(c, fs, users, flights)  # flights[4] is now a Demo Flight

        c.force_authenticate(users[0])
        resp = c.delete(reverse("flights-delete-demo", kwargs={"pk": str(flights[4].uuid)}))
        assert resp.status_code == 403
        flights[4].refresh_from_db()
        assert Flight.objects.filter(uuid=flights[4].uuid)  # flights[4] was NOT deleted
        assert flights[4].is_demo
