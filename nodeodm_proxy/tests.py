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
    other = User.objects.create_user(username="other", email="other@example.com", password="other",
                                     type=UserType.ACTIVE.name)
    Token.objects.create(user=admin)
    Token.objects.create(user=other)
    return admin, other


@pytest.fixture
def flights(users: List[User]):
    httpretty.enable()
    httpretty.register_uri(httpretty.POST, "http://container-nodeodm:3000/task/new/init", body="")
    httpretty.register_uri(httpretty.POST, re.compile(r"http://container-webhook-adapter:8080/register/.+"),
                           status=200)
    f1 = users[0].flight_set.create(name="flight1", date=datetime.now())
    f1.camera = Camera.RGB.name
    f1.save()
    f2 = Flight.objects.create(name="flight2", date=datetime.now(), is_demo=True)
    f2.camera = Camera.RGB.name
    f2.save()
    return f1, f2


# https://docs.pytest.org/en/latest/yieldfixture.html
@pytest.fixture(autouse=True)
def clear_httpretty():
    yield  # this runs each test
    httpretty.reset()


def _auth(c, user: User):
    """
    A helper function that configures an APIClient with the appropriate auth token for a User
    Args:
        c: An APIClient that will now send the user's token with all requests
        user: The User whose token will be used to authenticate all requests

    Returns: Nothing, but the passed APIClient will have its configuration changed
    """
    token = Token.objects.get(user=user)
    c.credentials(HTTP_AUTHORIZATION='Token ' + token.key)


def test_info_working_flight(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/info for an in-progress Flight works
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    mock_data = {"fake": "exists", "anotherFake": "alsoExists", "dummyCount": 100}
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/info",
                           body=json.dumps(mock_data))

    _auth(c, users[0])
    requests_before = len(httpretty.latest_requests)
    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    assert "anotherFake" in json.loads(resp.content)
    # one additional request to container-nodeodm/task/info
    assert len(httpretty.latest_requests) == requests_before + 1


@pytest.mark.xfail(reason="Request fires from localhost and httpretty patches gethostbyname to always return 127.0.0.1")
def test_info_working_flight_other_user(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/info for an in-progress Flight rejects the request if the user is not the owner
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    mock_data = {"fake": "exists", "anotherFake": "alsoExists", "dummyCount": 100}
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/info",
                           body=json.dumps(mock_data))

    _auth(c, users[1])
    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 403


def test_info_demo_flight(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/info for a demo Flight succeds even if the user is not the Flight owner
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[1].uuid}/info",
                           body=json.dumps({}))

    _auth(c, users[1])
    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[1].uuid}))
    assert resp.status_code == 200


def test_info_complete_flight(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/info for a complete Flight works
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    # this mock_data should NOT be returned
    mock_data = {"fake": "exists", "anotherFake": "alsoExists", "dummyCount": 100}
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/info",
                           body=json.dumps(mock_data))

    # manually mark the Flight as complete on DB
    flights[0].state = FlightState.COMPLETE.name
    flights[0].processing_time = 12345
    flights[0].save()

    _auth(c, users[0])
    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert "anotherFake" not in data
    assert data["processingTime"] == 12345
    assert data["status"]["code"] == 40


def test_info_forwards_404(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/info sends a 404 error if the backend answered with a 404
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/info",
                           status=404)

    # try to get info on working flight
    _auth(c, users[0])
    resp = c.get(reverse('nodeodm_proxy_task_info', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 404


def test_console_working_flight(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/output for an in-progress Flight works
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    mock_data = ["line1", "line2", "...", "line1000"]
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/output",
                           body=json.dumps(mock_data))

    _auth(c, users[0])
    resp = c.get(reverse('nodeodm_proxy_task_output', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    assert json.loads(resp.content)[3] == "line1000"


def test_console_other_user(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/output fails when the user is not the Flight owner
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    mock_data = ["line1", "line2", "...", "line1000"]
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/output",
                           body=json.dumps(mock_data))

    _auth(c, users[1])
    resp = c.get(reverse('nodeodm_proxy_task_output', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 403


def test_console_complete_flight(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/output for a complete Flight works
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    # this mock_data should NOT be returned
    mock_data = ["line1", "line2", "...", "line1000"]
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/output",
                           body=json.dumps(mock_data))

    # manually mark the Flight as complete on DB
    flights[0].state = FlightState.COMPLETE.name
    flights[0].save()

    _auth(c, users[0])
    resp = c.get(reverse('nodeodm_proxy_task_output', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 200
    assert resp.content.decode("utf-8") == "Vuelo completo"


def test_console_forwards_404(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/???/output sends a 404 error if the backend answered with a 404
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """
    httpretty.register_uri(httpretty.GET, f"http://container-nodeodm:3000/task/{flights[0].uuid}/output",
                           status=404)

    # try to get info on working flight
    _auth(c, users[0])
    resp = c.get(reverse('nodeodm_proxy_task_output', kwargs={"uuid": flights[0].uuid}))
    assert resp.status_code == 404


def test_cancel_task(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/task/cancel sends the cancellation request to the NodeODM backend
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """

    def callback(request: HTTPrettyRequest, uri, response_headers):
        body = request.parsed_body
        assert "uuid" in body
        # body[uuid] is a list, probably to support repeated keys
        assert body["uuid"][0] == str(flights[0].uuid)
        return [204, response_headers, ""]

    httpretty.register_uri(httpretty.POST, f"http://container-nodeodm:3000/task/cancel",
                           body=callback)
    _auth(c, users[0])
    resp = c.post(reverse('nodeodm_proxy_task_cancel'), {"uuid": str(flights[0].uuid)}, format="json")
    assert resp.status_code == 204


def test_cancel_task_fails(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/task/cancel sends a 404 error if the backend answered with a 404
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """

    def callback(request: HTTPrettyRequest, uri, response_headers):
        return [404, response_headers, ""]

    httpretty.register_uri(httpretty.POST, f"http://container-nodeodm:3000/task/cancel",
                           body=callback)
    _auth(c, users[0])
    resp = c.post(reverse('nodeodm_proxy_task_cancel'), {"uuid": str(flights[0].uuid)}, format="json")
    assert resp.status_code == 404


def test_cancel_task_other_user(c, users: List[User], flights: List[Flight]):
    """
    Tests that calling /nodeodm/task/cancel fails when the user is not the Flight owner
    Args:
        c: The APIClient fixture that will send the request
        users: A fixture containing Users
        flights: A fixture containing Flights
    """

    def callback(request: HTTPrettyRequest, uri, response_headers):
        body = request.parsed_body
        assert "uuid" in body
        # body[uuid] is a list, probably to support repeated keys
        assert body["uuid"][0] == str(flights[0].uuid)
        return [204, response_headers, ""]

    httpretty.register_uri(httpretty.POST, f"http://container-nodeodm:3000/task/cancel",
                           body=callback)
    _auth(c, users[1])
    requests_before = len(httpretty.latest_requests)
    resp = c.post(reverse('nodeodm_proxy_task_cancel'), {"uuid": str(flights[0].uuid)}, format="json")
    assert resp.status_code == 403
    assert len(httpretty.latest_requests) == requests_before  # no additional requests must have been called
