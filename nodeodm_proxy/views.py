import json

from django.conf import settings
from django.http import HttpResponse
import requests

from django.views.decorators.csrf import csrf_exempt

from nodeodm_proxy import api


def task_info(request, uuid):
    response = api.get_info(settings.NODEODM_SERVER_URL, uuid, settings.NODEODM_SERVER_TOKEN)
    return HttpResponse(content=response.content, status=response.status_code)


def task_output(request, uuid):
    response = requests.get(f"{settings.NODEODM_SERVER_URL}/task/{uuid}/output?token={settings.NODEODM_SERVER_TOKEN}")
    return HttpResponse(content=response.content, status=response.status_code)


@csrf_exempt
def cancel_task(request):
    data = json.loads(request.body.decode("utf-8"))
    uuid = data["uuid"]
    response = requests.post(f"{settings.NODEODM_SERVER_URL}/task/cancel?token={settings.NODEODM_SERVER_TOKEN}",
                             data={"uuid": uuid})
    return HttpResponse(status=response.status_code)
