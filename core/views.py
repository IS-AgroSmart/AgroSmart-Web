# ViewSets define the view behavior.
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.models import *
from core.permissions import OnlySelfUnlessAdminPermission
from core.serializers import *


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, OnlySelfUnlessAdminPermission,)
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.all() if self.request.user.is_staff else User.objects.filter(pk=self.request.user.pk)


class FlightViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = FlightSerializer

    def get_queryset(self):
        return Flight.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_staff or "target_user" not in self.request.POST:
            serializer.save(user=self.request.user)
        else:
            serializer.save(user=User.objects.get(pk=self.request.POST["target_user"]))


@csrf_exempt
def upload_images(request, uuid):
    flight = get_object_or_404(Flight, uuid=uuid)

    files = []
    for f in request.FILES.getlist("images"):
        path = default_storage.save('tmp/' + f.name, ContentFile(f.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        files.append(('images', open(tmp_file, "rb")))
    r = requests.post("http://localhost:3000/task/new/upload/" + str(flight.uuid), files=files)
    if r.status_code != 200:
        return HttpResponse(status=500)
    r = requests.post("http://localhost:3000/task/new/commit/" + str(flight.uuid))
    if r.status_code != 200:
        return HttpResponse(status=500)
    r = requests.get("http://localhost:3000/task/" + str(flight.uuid) + "/info")
    flight.state = FlightState.PROCESSING.name
    flight.save()

    return HttpResponse()
