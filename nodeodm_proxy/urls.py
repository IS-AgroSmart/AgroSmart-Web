from django.urls import path

from nodeodm_proxy import views

urlpatterns = [
    path('task/<uuid:uuid>/info', views.task_info, name="nodeodm_proxy_task_info"),
    path('task/<uuid:uuid>/output', views.task_output, name="nodeodm_proxy_task_output"),
    path('task/cancel', views.cancel_task, name="nodeodm_proxy_task_cancel"),
]
