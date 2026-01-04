from django.contrib import admin

from core import models


class ImmutableModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(models.Wallet, ImmutableModelAdmin)
admin.site.register(models.Transaction, ImmutableModelAdmin)
