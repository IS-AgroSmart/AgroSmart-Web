from django.db.models import Count, Sum, Window, F, Case, When
from django.http import HttpResponse
from django.shortcuts import render

from core.models import User, UserType, Flight


def metrics(request):
    users = User.objects.values("type").annotate(count=Count("*"))
    flights = Flight.objects.values("state").annotate(count=Count("*"))

    images_per_flight_sum = Flight.objects.aggregate(total=Sum("num_images"))["total"]
    images_per_flight_count = Flight.objects.count()
    images_per_flight = []
    for stop in [50, 100, 200, 500, 1000]:
        images_per_flight.append((stop, Flight.objects.filter(num_images__lte=stop).count()))

    return render(request, "exposition.txt", {
        "users": users,
        "flights": flights,
        "images_per_flight": images_per_flight,
        "images_per_flight_sum": images_per_flight_sum,
        "images_per_flight_count": images_per_flight_count
    })
