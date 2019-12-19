from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import *

admin.site.register(User)
admin.site.register(Flight)
admin.site.register(Artifact)
admin.site.register(UserProject)
admin.site.register(DemoProject)

