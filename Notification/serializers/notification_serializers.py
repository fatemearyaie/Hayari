from rest_framework import serializers

from Notification.models.notification_models import UserNotification


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = '__all__'
        read_only_fields = ['user','title','description', 'created_at', 'updated_at']