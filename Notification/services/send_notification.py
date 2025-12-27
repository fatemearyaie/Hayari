# from celery import shared_task
import threading
from firebase_admin import messaging
from Notification.models.notification_models import UserNotification,UserFCMToken
from core.firebase import get_firebase_app


def get_title(message_type):
    titles = {
        'ad_accepted': 'Ad Accepted',
        'donation_success': 'Donation Successful',
        'ad_rejected': 'Ad Rejected',
    }

    return titles.get(message_type, 'New Message')


def get_description(message_type):


    descriptions = {
        'ad_accepted': 'Your Ad has been accepted',
        'donation_success': 'Your donation was completed successfully',
        'ad_rejected': 'Your Ad has been Rejected!',
    }
    return descriptions.get(message_type, '')


def send_notification(user,message_type,related_user=None,description=None,extra_data=None,):
    try:
        title = get_title(message_type)

        if description is None:
            base_desc = get_description(message_type)
            if related_user:
                final_desc = f"{related_user.user_name} {base_desc}".strip()
            else:
                final_desc = base_desc
        else:
            if related_user:
                final_desc = f"{related_user.user_name} {description}".strip()
            else:
                final_desc = str(description)

        notif = UserNotification.objects.create(
            user=user,
            title=title,
            description=final_desc,
        )
    except Exception:
        title = get_title(message_type)
        if description is None:
            base_desc = get_description(message_type)
            final_desc = f"{getattr(related_user, 'user_name', '')} {base_desc}".strip()
        else:
            final_desc = f"{getattr(related_user, 'user_name', '')} {description}".strip()

    try:
        fcm_obj = UserFCMToken.objects.filter(user=user).first()
        if not fcm_obj or not fcm_obj.token:
            return

        data = {
            'title': str(title),
            'message': str(final_desc),
            'fcm': str(fcm_obj.token),
        }

        if extra_data and isinstance(extra_data, dict):
            for k, v in extra_data.items():
                data[str(k)] = str(v)

        thread = threading.Thread(
            target=send_firebase,
            args=(data,),
            daemon=True
        )
        thread.start()

    except Exception:
        return


# @shared_task
def send_firebase(data):
    app = get_firebase_app()

    payload = dict(data)
    token = payload.pop('fcm', None)
    title = payload.pop('title', '')
    body = payload.pop('message', '')

    payload = {str(k): str(v) for k, v in payload.items()}

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=payload if payload else None,
        token=token,
    )

    try:
        response = messaging.send(message, app=app)
        print("Successfully sent FCM message:", response)

    except messaging.UnregisteredError:
        if token:
            UserFCMToken.objects.filter(token=token).delete()
        print("FCM token unregistered. Deleted token.")

    except Exception as e:
        print("Error sending FCM notification:", str(e))
