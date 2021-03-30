from django.urls import path

from prometheus_metrics import views

urlpatterns = [
    path('', views.metrics),
]
