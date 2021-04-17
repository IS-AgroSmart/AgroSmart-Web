import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
import requests

from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token

from core.models import Flight, FlightState, UserType
from nodeodm_proxy import api

_NODEODM_STATUS_CODES = {FlightState.COMPLETE.name: 40, FlightState.ERROR.name: 30, FlightState.CANCELED.name: 50}


def task_info(request, uuid):
    user = Token.objects.get(key=request.headers["Authorization"][6:]).user
    flight = Flight.objects.get(uuid=uuid)

    if not user.type == UserType.ADMIN.name and not flight.user == user:
        return HttpResponse(status=403)

    if flight.state in _NODEODM_STATUS_CODES:  # Flight has ended, return cached values
        data = {
            "status": {"code": _NODEODM_STATUS_CODES[flight.state]},
            "processingTime": flight.processing_time,
            "imagesCount": flight.num_images
        }
        return JsonResponse(data)
    else:  # hit the NodeODM API
        response = api.get_info(settings.NODEODM_SERVER_URL, uuid, settings.NODEODM_SERVER_TOKEN)
        return HttpResponse(content=response.content, status=response.status_code)


def task_output(request, uuid):
    user = Token.objects.get(key=request.headers["Authorization"][6:]).user
    flight = Flight.objects.get(uuid=uuid)

    if not user.type == UserType.ADMIN.name and not flight.user == user:
        return HttpResponse(status=403)

    if flight.state in _NODEODM_STATUS_CODES:  # Flight has ended, return hardcoded value
        return HttpResponse(b"Vuelo completo")
    else:  # hit the NodeODM API
        response = requests.get(
            f"{settings.NODEODM_SERVER_URL}/task/{uuid}/output?token={settings.NODEODM_SERVER_TOKEN}")
        return HttpResponse(content=response.content, status=response.status_code)


@csrf_exempt
def cancel_task(request):
    user = Token.objects.get(key=request.headers["Authorization"][6:]).user
    data = json.loads(request.body.decode("utf-8"))
    uuid = data["uuid"]
    flight = Flight.objects.get(uuid=uuid)

    if not user.type == UserType.ADMIN.name and not flight.user == user:
        return HttpResponse(status=403)

    response = requests.post(f"{settings.NODEODM_SERVER_URL}/task/cancel?token={settings.NODEODM_SERVER_TOKEN}",
                             data={"uuid": uuid})
    return HttpResponse(status=response.status_code)
