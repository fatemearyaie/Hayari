from Notification.models.notification_models import UserNotification


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


def send_notification(user, message_type, related_user=None, description=None):
    title = get_title(message_type)

    if description is None:
        base_desc = get_description(message_type)
        final_desc = f"{related_user.user_name} {base_desc}".strip() if related_user else base_desc
    else:
        final_desc = f"{related_user.user_name} {description}".strip() if related_user else str(description)

    return UserNotification.objects.create(
        user=user,
        title=title,
        description=final_desc,
    )
