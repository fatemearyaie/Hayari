from django.db.models.signals import post_save,pre_save
from django.dispatch import receiver
from Notification.models.notification_models import UserNotification, UserFCMToken
from Notification.tasks import send_firebase_task
from django.db import transaction


@receiver(pre_save, sender=UserFCMToken)
def enforce_single_fcm_per_user(sender, instance: UserFCMToken, **kwargs):
    if not instance.user_id:
        return

    with transaction.atomic():
        if instance.token:
            UserFCMToken.objects.filter(token=instance.token).exclude(user_id=instance.user_id).delete()

        qs = UserFCMToken.objects.filter(user_id=instance.user_id)
        if instance.pk:
            qs = qs.exclude(pk=instance.pk)
        qs.delete()


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
        "extra": {
            "type": "notification",
            "notification_id": str(instance.id),
        }
    }
    send_firebase_task.delay(data)