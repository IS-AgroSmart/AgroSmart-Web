from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import *


def _format_size(size):
    """
    Pretty-prints a disk size for human consumption
    Args:
        size: The size to format, in kilobytes

    Returns: A string of the form "3.4567 GB" (two decimals, in gigabytes)
    """
    return f"{size / (1024 ** 2):.4f} GB"


def recompute_disk_space(modeladmin, request, queryset):
    for obj in queryset:
        obj.update_disk_space()


recompute_disk_space.short_description = "Recompute disk space used by the selected object(s)"


class FlightAdmin(admin.ModelAdmin):
    def pretty_used_space(self, obj: Flight):
        return _format_size(obj.used_space)

    pretty_used_space.short_description = "Used space"

    list_display = ("name", "uuid", "user", "date", "camera", "state", "pretty_used_space")

    actions = (recompute_disk_space,)


class UserProjectAdmin(admin.ModelAdmin):
    def pretty_used_space(self, obj: UserProject):
        return _format_size(obj.used_space)

    pretty_used_space.short_description = "Used space"

    list_display = ("name", "uuid", "pretty_used_space")

    actions = (recompute_disk_space,)


class CustomUserAdmin(UserAdmin):
    def pretty_used_space(self, obj: User):
        return _format_size(obj.used_space)

    pretty_used_space.short_description = "Used space"

    def pretty_maximum_space(self, obj: User):
        return _format_size(obj.maximum_space)

    pretty_maximum_space.short_description = "Maximum space"

    def refresh_available_images(self, request, queryset):
        for obj in queryset:
            obj.remaining_images = obj.image_month_quota
            obj.save()

    refresh_available_images.short_description = "Reset image quota for the selected users(s)"

    list_display = UserAdmin.list_display + ("pretty_used_space", "pretty_maximum_space",
                                             "remaining_images")

    fieldsets = UserAdmin.fieldsets + (
        ("Additional data", {'fields': ('type', 'used_space', 'maximum_space',
                                        'remaining_images', 'image_month_quota')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('type',)}),
    )

    actions = (recompute_disk_space, "refresh_available_images")


admin.site.register(User, CustomUserAdmin)
admin.site.register(Flight, FlightAdmin)
admin.site.register(Artifact)
admin.site.register(UserProject, UserProjectAdmin)
