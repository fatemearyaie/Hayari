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


class UserFCMToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=1000, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'FCM Token'
        verbose_name_plural = 'FCM Tokens'
        indexes = [
            models.Index(fields=['user'], name='idx_userfcm_user'),
            models.Index(fields=['token'], name='idx_userfcm_token'),
        ]

    def __str__(self):
        return self.user.username