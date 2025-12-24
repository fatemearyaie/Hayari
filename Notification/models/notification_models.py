from django.db import models

from Users.models import CustomUser


# Create your models here.
class UserNotification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=20, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Notification'
        verbose_name_plural = 'User Notifications'

        indexes = [
            models.Index(fields=['is_read'], name='idx_notification_is_read'),
            models.Index(fields=['created_at'], name='idx_notification_created_at'),
        ]
        ordering = ['-created_at']