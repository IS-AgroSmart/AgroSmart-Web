import io
import json
import os
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from httpretty import httpretty
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from core.models import FlightState, UserType

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
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/init", body="")
    f1 = users[0].flight_set.create(name="flight1", date=datetime.now())
    return f1,


@pytest.fixture
def c():
    return APIClient()


def _auth(c, user):
    token = Token.objects.get(user=user)
    c.credentials(HTTP_AUTHORIZATION='Token ' + token.key)


def test_upload_images_succesful(c, users, flights, fs):
    _auth(c, users[0])
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/upload/" + str(flights[0].uuid), "")
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/commit/" + str(flights[0].uuid), "")
    fs.create_file("/tmp/image1.jpg", contents="foobar")
    with open("/tmp/image1.jpg") as f:
        resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}), {"images": f})
        assert resp.status_code == 200


def test_upload_images_error_on_creation(c, users, flights, fs):
    import inspect
    import django, pytz

    _auth(c, users[0])
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/upload/" + str(flights[0].uuid), "",
                           status=500)
    fs.add_real_directory(os.path.dirname(inspect.getfile(django)))
    fs.add_real_directory(os.path.dirname(inspect.getfile(pytz)))
    resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 500


def test_upload_images_error_on_commit(c, users, flights, fs):
    import inspect
    import django, pytz

    _auth(c, users[0])
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/upload/" + str(flights[0].uuid), "")
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/commit/" + str(flights[0].uuid), "",
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
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/upload/" + str(flights[0].uuid), "")
    httpretty.register_uri(httpretty.POST, "http://localhost:3000/task/new/commit/" + str(flights[0].uuid), "")
    resp = c.post(reverse('upload_files', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200


def _test_webhook(c, flight, code):
    executed = False

    def mark_executed(request, uri, response_headers):
        nonlocal executed
        executed = True
        return [200, response_headers, ""]

    httpretty.register_uri(httpretty.POST, "http://localhost/geoserver/geoserver/rest/workspaces", "")
    httpretty.register_uri(httpretty.PUT, "http://localhost/geoserver/geoserver/rest/workspaces/flight_" +
                           str(flight.uuid) + "/coveragestores/ortho/external.geotiff", mark_executed)
    resp = c.post(reverse("webhook"), json.dumps(
        {"uuid": str(flight.uuid), "status": {"code": code}}), content_type="application/text")
    assert executed
    return resp


def test_webhook_successful(c, flights):
    resp = _test_webhook(c, flights[0], code=40)
    assert resp.status_code == 200
    flights[0].refresh_from_db()  # HACK seems to be necessary to reload status?
    assert flights[0].state == FlightState.COMPLETE.name
    # TODO maybe assert that the Geoserver APIs are called, if possible


def test_webhook_with_error(c, flights):
    resp = _test_webhook(c, flights[0], code=30)
    assert resp.status_code == 200
    flights[0].refresh_from_db()
    assert flights[0].state == FlightState.ERROR.name


def test_webhook_canceled(c, flights):
    resp = _test_webhook(c, flights[0], code=50)
    assert resp.status_code == 200
    flights[0].refresh_from_db()
    assert flights[0].state == FlightState.CANCELED.name


def test_download_artifact(c, flights, fs):
    uuid = str(flights[0].uuid)
    fs.create_file("/flights/" + uuid + "/odm_orthophoto/odm_orthophoto.png", contents="PNG orthomosaic")
    fs.create_file("/flights/" + uuid + "/odm_orthophoto/odm_orthophoto.tif", contents="barbaz")
    fs.create_file("/flights/" + uuid + "/odm_meshing/odm_mesh.ply", contents="the 3d mesh")
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "orthomosaic.png"}))
    # Iterator juggling, streaming_content must be forced to return its first value
    assert next(resp.streaming_content).decode("utf-8") == "PNG orthomosaic"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "3dmodel"}))
    assert next(resp.streaming_content).decode("utf-8") == "the 3d mesh"
    resp = c.get(reverse("download_artifact", kwargs={"uuid": uuid, "artifact": "someunknownartifact"}))
    assert resp.status_code == 404


def test_formula_checker_endpoint(c):
    assert c.post(reverse("check_formula"), {"formula": "(red+  blue)"}).status_code == 200
    assert c.post(reverse("check_formula"), {"formula": "(red+  blue"}).status_code == 400
    assert c.post(reverse("check_formula"), {"formula": "foobar"}).status_code == 400
