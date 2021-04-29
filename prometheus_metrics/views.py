import os
import subprocess

from django.db.models import Count, Sum, Window, F, Case, When
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from core.models import User, UserType, Flight
from core.utils.working_dir import cd


def _get_git_info():
    with cd("/gitinfo"):
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        try:
            version = subprocess.check_output(["git", "describe"], stderr=subprocess.STDOUT, text=True).strip()
        except subprocess.CalledProcessError as e:
            assert e.output.startswith("fatal:"), f"Message {e.output} should have begun with fatal"
            version = "<label not found>"

    return {"version": version, "revision": revision, "branch": branch}


@require_http_methods(request_method_list=["GET"])
def metrics(request):
    users = User.objects.values("type").annotate(count=Count("*"))
    flights = Flight.objects.values("state").annotate(count=Count("*"))

    images_per_flight_sum = Flight.objects.aggregate(total=Sum("num_images"))["total"]
    images_per_flight_count = Flight.objects.count()
    images_per_flight = []
    for stop in [50, 100, 200, 500, 1000]:
        images_per_flight.append((stop, Flight.objects.filter(num_images__lte=stop).count()))

    space_per_user_sum = User.objects.aggregate(total=Sum("used_space"))["total"]
    space_per_user_count = User.objects.count()
    space_per_user = []
    for stop in [1, 5, 10, 20, 45]:
        space_per_user.append((stop, User.objects.filter(used_space__lte=stop * 1024 ** 2).count()))

    images_per_user_sum = User.objects.aggregate(total=Sum("remaining_images"))["total"]
    images_per_user_count = User.objects.count()
    images_per_user = []
    for stop in [100, 200, 500, 1000, 2000, 3000]:
        images_per_user.append((stop, User.objects.filter(remaining_images__lte=stop).count()))

    build_info = _get_git_info()

    return render(request, "exposition.txt", {
        "users": users,
        "flights": flights,
        "images_per_flight": images_per_flight,
        "images_per_flight_sum": images_per_flight_sum,
        "images_per_flight_count": images_per_flight_count,
        "space_per_user": space_per_user,
        "space_per_user_sum": space_per_user_sum,
        "space_per_user_count": space_per_user_count,
        "images_per_user": images_per_user,
        "images_per_user_sum": images_per_user_sum,
        "images_per_user_count": images_per_user_count,
        "build_info": build_info
    })
