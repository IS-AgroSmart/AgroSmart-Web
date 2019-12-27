from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import *


class FlightAdmin(admin.ModelAdmin):
    list_display = ("name", "uuid", "user", "date", "camera", "multispectral_processing", "state")


admin.site.register(User, UserAdmin)
admin.site.register(Flight, FlightAdmin)
admin.site.register(Artifact)
admin.site.register(UserProject)
admin.site.register(DemoProject)
