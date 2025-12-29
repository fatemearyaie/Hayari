from celery import shared_task
from firebase_admin import messaging

from core.firebase import get_firebase_app
from Notification.models.notification_models import UserFCMToken


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_firebase_task(self, data: dict):

    try:
        app = get_firebase_app()

        payload = dict(data)
        token = payload.pop("fcm", None)
        title = payload.pop("title", "")
        body = payload.pop("message", "")

        payload = {str(k): str(v) for k, v in payload.items()}

        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=payload if payload else None,
            token=token,
        )

        resp = messaging.send(msg, app=app)
        return {"success": True, "message_id": resp}

    except messaging.UnregisteredError:
        if data.get("fcm"):
            UserFCMToken.objects.filter(token=data["fcm"]).delete()
        return {"success": False, "error": "unregistered"}

    except Exception as e:
        raise self.retry(exc=e)
