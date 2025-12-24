from django.contrib import admin
from django.contrib.admin import ModelAdmin

from Notification.models.notification_models import UserNotification


@admin.register(UserNotification)
class UserNotificationAdmin(ModelAdmin):
    list_display = ['user', 'title', 'is_read', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'user']
    list_filter = ['is_read', 'created_at']
    ordering = ['-created_at']
