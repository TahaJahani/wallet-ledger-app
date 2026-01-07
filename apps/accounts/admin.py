from django.contrib import admin

from . import models


@admin.register(models.User)
class UserModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False
