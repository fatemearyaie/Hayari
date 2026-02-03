from django.contrib import admin
from unfold.admin import ModelAdmin

from Notification.models.notification_models import UserNotification, UserFCMToken


@admin.register(UserNotification)
class UserNotificationAdmin(ModelAdmin):
    list_display = ['user', 'title', 'is_read', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'user']
    list_filter = ['is_read', 'created_at']
    ordering = ['-created_at']


@admin.register(UserFCMToken)
class UserFCMTokenAdmin(ModelAdmin):
    list_display = (
        'id',
        'user',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'user__username',
        'user__phone',
        'token',
    )

    list_filter = (
        'created_at',
        'updated_at',
    )