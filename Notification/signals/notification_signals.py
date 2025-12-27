from django.db.models.signals import post_save
from django.dispatch import receiver

from Notification.models.notification_models import UserNotification, UserFCMToken
from Notification.services.send_notification import send_firebase


@receiver(post_save, sender=UserNotification)
def send_fcm_on_notification_created(sender, instance: UserNotification, created: bool, **kwargs):
    if not created:
        return

    fcm_obj = UserFCMToken.objects.filter(user=instance.user).first()
    if not fcm_obj or not fcm_obj.token:
        return

    data = {
        "title": str(instance.title),
        "message": str(instance.description or ""),
        "fcm": str(fcm_obj.token),
    }
    send_firebase(data)
