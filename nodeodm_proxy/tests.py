import json
import re
from datetime import datetime
from typing import List

import pytest
from django.urls import reverse
from httpretty import httpretty
from httpretty.core import HTTPrettyRequest
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from core.models import Camera, UserType, Flight, User, FlightState

pytestmark = pytest.mark.django_db


@pytest.fixture
def c():
    return APIClient()


@pytest.fixture
def users():
    admin = User.objects.create_user(username="admin", email="admin@example.com", password="admin",
                                     type=UserType.ADMIN.name)
    Token.objects.create(user=admin)
    return admin,


@pytest.fixture
def flights(users: List[User]):
    httpretty.enable()
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/init", body="")
    httpretty.register_uri(httpretty.POST, re.compile(r"http://container-webhook-adapter:8080/register/.+"),
                           status=200)
    f1 = users[0].flight_set.create(name="flight1", date=datetime.now())
    f1.camera = Camera.RGB.name
    f1.save()
    return f1,


def test_info_working_flight(c, flights: List[Flight]):
    mock_data = {"fake": "exists", "anotherFake": "alsoExists", "dummyCount": 100}
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/info",
                           body=json.dumps(mock_data))

    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    assert "anotherFake" in json.loads(resp.content)


def test_info_complete_flight(c, flights: List[Flight]):
    # this mock_data should NOT be returned
    mock_data = {"fake": "exists", "anotherFake": "alsoExists", "dummyCount": 100}
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/info",
                           body=json.dumps(mock_data))

    # manually mark the Flight as complete on DB
    flights[0].state = FlightState.COMPLETE.name
    flights[0].processing_time = 12345
    flights[0].save()

    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert "anotherFake" not in data
    assert data["processingTime"] == 12345
    assert data["status"]["code"] == 40


def test_info_forwards_404(c, flights: List[Flight]):
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/info",
                           status=404)

    # try to get info on working flight
    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 404


def test_console_working_flight(c, flights: List[Flight]):
    mock_data = ["line1", "line2", "...", "line1000"]
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/output",
                           body=json.dumps(mock_data))

    resp = c.get(reverse('nodeodm_proxy_task_output', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    assert json.loads(resp.content)[3] == "line1000"


def test_console_complete_flight(c, flights: List[Flight]):
    # this mock_data should NOT be returned
    mock_data = ["line1", "line2", "...", "line1000"]
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/output",
                           body=json.dumps(mock_data))

    # manually mark the Flight as complete on DB
    flights[0].state = FlightState.COMPLETE.name
    flights[0].save()

    resp = c.get(reverse('nodeodm_proxy_task_output', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    assert resp.content.decode("utf-8") == "Vuelo completo"


def test_console_forwards_404(c, flights: List[Flight]):
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/output",
                           status=404)

    # try to get info on working flight
    resp = c.get(reverse('nodeodm_proxy_task_output', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 404


def test_cancel_task(c, flights: List[Flight]):
    def callback(request: HTTPrettyRequest, uri, response_headers):
        body = request.parsed_body
        assert "uuid" in body
        # body[uuid] is a list, probably to support repeated keys
        assert body["uuid"][0] == str(flights[0].uuid)
        return [204, response_headers, ""]

    httpretty.register_uri(httpretty.POST, f"http://container-nodeodm:3000/task/cancel",
                           body=callback)
    resp = c.post(reverse('nodeodm_proxy_task_cancel'), {"uuid": str(flights[0].uuid)}, format="json")
    assert resp.status_code == 204


def test_cancel_task_fails(c, flights: List[Flight]):
    def callback(request: HTTPrettyRequest, uri, response_headers):
        return [404, response_headers, ""]

    httpretty.register_uri(httpretty.POST, f"http://container-nodeodm:3000/task/cancel",
                           body=callback)
    resp = c.post(reverse('nodeodm_proxy_task_cancel'), {"uuid": str(flights[0].uuid)}, format="json")
    assert resp.status_code == 404
