"""IngSoft1 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from core.views import *

router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename="users")
router.register(r'flights', FlightViewSet, basename="flights")
router.register(r'projects', UserProjectViewSet, basename="projects")
router.register(r'artifacts', ArtifactViewSet, basename="artifacts")

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'api/', include(router.urls)),
    path('api/api-auth', obtain_auth_token, name='api_auth'),
    path('api/upload-files/<uuid:uuid>', upload_images),
    path('api/webhook-processing-complete', webhook_processing_complete),
    path('api/downloads/<uuid:uuid>/<artifact>', download_artifact),
    path('api/preview/<uuid:uuid>', preview_flight_url),
    path('api/preview4/<uuid:uuid>', preview_flight_url)
]
