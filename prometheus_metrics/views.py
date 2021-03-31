import os
import subprocess

from django.db.models import Count, Sum, Window, F, Case, When
from django.http import HttpResponse
from django.shortcuts import render

from core.models import User, UserType, Flight


def _get_git_info():
    original_dir = os.getcwd()
    os.chdir("/gitinfo")

    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    try:
        version = subprocess.check_output(["git", "describe"], stderr=subprocess.STDOUT, text=True).strip()
    except subprocess.CalledProcessError as e:
        assert e.output.startswith("fatal:"), f"Message {e.output} should have begun with fatal"
        version = ""

    os.chdir(original_dir)
    return {"version": version, "revision": revision, "branch": branch}


def metrics(request):
    users = User.objects.values("type").annotate(count=Count("*"))
    flights = Flight.objects.values("state").annotate(count=Count("*"))

    images_per_flight_sum = Flight.objects.aggregate(total=Sum("num_images"))["total"]
    images_per_flight_count = Flight.objects.count()
    images_per_flight = []
    for stop in [50, 100, 200, 500, 1000]:
        images_per_flight.append((stop, Flight.objects.filter(num_images__lte=stop).count()))

    build_info = _get_git_info()

    return render(request, "exposition.txt", {
        "users": users,
        "flights": flights,
        "images_per_flight": images_per_flight,
        "images_per_flight_sum": images_per_flight_sum,
        "images_per_flight_count": images_per_flight_count,
        "build_info": build_info
    })
