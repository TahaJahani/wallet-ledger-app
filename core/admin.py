from django.contrib import admin
from django.urls.base import reverse
from django.utils.html import format_html

from core import models


class ImmutableModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.Wallet)
class WalletModelAdmin(ImmutableModelAdmin):
    list_display = ("id", "user_link")
    readonly_fields = ("user_link",)

    def user_link(self, obj):
        url = reverse(
            "admin:%s_%s_change"
            % (obj.user._meta.app_label, obj.user._meta.model_name),
            args=[obj.user.pk],
        )
        return format_html('<a href="{}">{}</a>', url, obj.user)

    user_link.short_description = "User"


@admin.register(models.User)
class UserModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(models.Transaction, ImmutableModelAdmin)
