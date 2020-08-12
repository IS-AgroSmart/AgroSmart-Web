from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import *


class FlightAdmin(admin.ModelAdmin):
    list_display = ("name", "uuid", "user", "date", "camera", "multispectral_processing", "state")


class UserProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "uuid",)


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Additional data", {'fields': ('type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('type',)}),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Flight, FlightAdmin)
admin.site.register(Artifact)
admin.site.register(UserProject, UserProjectAdmin)
