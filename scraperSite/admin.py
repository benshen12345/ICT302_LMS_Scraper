from django.contrib import admin
from .models import User, ScanReport, UnsafeURL

admin.site.register(User)
admin.site.register(ScanReport)
admin.site.register(UnsafeURL)
