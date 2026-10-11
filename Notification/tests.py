from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase, TestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from Notification.models.notification_models import UserFCMToken, UserNotification
from Notification.serializers.notification_serializers import UserNotificationSerializer
from Notification.services.send_notification import (
    get_description,
    get_title,
    send_notification,
)
from Notification.tasks import send_firebase_task
from Users.models import CustomUser


def create_user(email):
    return CustomUser.objects.create_user(email=email)


def auth_headers(user):
    token = AccessToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


class NotificationMessageTests(SimpleTestCase):
    def test_supported_and_unknown_message_mappings(self):
        self.assertEqual(get_title("ad_accepted"), "تبلیغ تایید شد")
        self.assertEqual(get_title("donation_success"), "اهدا انجام شد")
        self.assertEqual(get_title("ad_rejected"), "تبلیغ رد شد")
        self.assertEqual(get_title("unknown"), "New Message")
        self.assertEqual(get_description("ad_accepted"), "تبلیغ شما تایید شد")
        self.assertEqual(get_description("donation_success"), "اهدای شما با موفقیت انجام شد")
        self.assertEqual(get_description("ad_rejected"), "تبلیغ شما رد شد!")
        self.assertEqual(get_description("unknown"), "")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "notification-tests",
        }
    }
)
class NotificationModelAndServiceTests(TestCase):
    def setUp(self):
        self.user = create_user("notification@example.com")
        self.other_user = create_user("notification-other@example.com")

    @patch("Notification.services.send_notification.UserNotification.objects.create")
    def test_send_notification_uses_supported_mapping_and_related_prefix(self, create):
        create.return_value = "created-notification"
        related = SimpleNamespace(user_name="Ali")
        result = send_notification(
            user=self.user,
            message_type="ad_accepted",
            related_user=related,
        )
        self.assertEqual(result, "created-notification")
        create.assert_called_once_with(
            user=self.user,
            title="تبلیغ تایید شد",
            description="Ali تبلیغ شما تایید شد",
        )

    @patch("Notification.services.send_notification.UserNotification.objects.create")
    def test_explicit_description_and_unknown_message_are_preserved(self, create):
        send_notification(
            user=self.user,
            message_type="unknown",
            description="Custom message",
        )
        create.assert_called_once_with(
            user=self.user,
            title="New Message",
            description="Custom message",
        )

    def test_notification_serializer_keeps_server_fields_read_only(self):
        notification = UserNotification.objects.create(
            user=self.user,
            title="Title",
            description="Description",
        )
        data = UserNotificationSerializer(notification).data
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["title"], "Title")
        self.assertEqual(data["description"], "Description")
        self.assertFalse(data["is_read"])
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

        update_serializer = UserNotificationSerializer(
            notification,
            data={
                "user": self.other_user.id,
                "title": "Changed title",
                "description": "Changed description",
                "is_read": True,
            },
            partial=True,
        )
        self.assertTrue(update_serializer.is_valid(), update_serializer.errors)
        self.assertEqual(update_serializer.validated_data, {"is_read": True})

    @patch("Notification.signals.notification_signals.send_firebase_task.delay")
    def test_notification_signal_queues_only_when_user_has_token(self, delay):
        token = UserFCMToken.objects.create(user=self.user, token="token-1")
        notification = UserNotification.objects.create(
            user=self.user,
            title="Title",
            description="Description",
        )
        delay.assert_called_once_with({
            "title": "Title",
            "message": "Description",
            "fcm": token.token,
            "extra": {
                "type": "notification",
                "notification_id": str(notification.id),
            },
        })

        delay.reset_mock()
        UserNotification.objects.create(user=self.other_user, title="No token")
        UserFCMToken.objects.create(user=self.other_user, token="")
        UserNotification.objects.create(user=self.other_user, title="Blank token")
        delay.assert_not_called()

    def test_fcm_signal_keeps_one_token_per_user_and_reassigns_token(self):
        first = UserFCMToken.objects.create(user=self.user, token="same-token")
        second = UserFCMToken.objects.create(user=self.user, token="other-token")
        self.assertFalse(UserFCMToken.objects.filter(pk=first.pk).exists())
        self.assertTrue(UserFCMToken.objects.filter(pk=second.pk).exists())

        reassigned = UserFCMToken.objects.create(user=self.other_user, token="other-token")
        self.assertTrue(UserFCMToken.objects.filter(pk=reassigned.pk, user=self.other_user).exists())
        self.assertFalse(UserFCMToken.objects.filter(pk=second.pk).exists())


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "notification-http-tests",
        }
    }
)
class NotificationHttpTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user("notification-http@example.com")
        self.other_user = create_user("notification-http-other@example.com")

    @patch("Notification.signals.notification_signals.send_firebase_task.delay")
    def test_notification_list_filter_and_read_actions_are_user_scoped(self, delay):
        own_unread = UserNotification.objects.create(
            user=self.user,
            title="Unread",
            description="One",
        )
        own_read = UserNotification.objects.create(
            user=self.user,
            title="Read",
            description="Two",
            is_read=True,
        )
        other = UserNotification.objects.create(
            user=self.other_user,
            title="Other",
            description="Other",
        )
        delay.reset_mock()

        listing = self.client.get("/api/v1/notifications/notif/", **auth_headers(self.user))
        unread = self.client.get("/api/v1/notifications/notif/?is_read=false", **auth_headers(self.user))
        count = self.client.get("/api/v1/notifications/notif/unread_count/", **auth_headers(self.user))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            {item["id"] for item in listing.json()["data"]["results"]},
            {own_unread.id, own_read.id},
        )
        self.assertEqual([item["id"] for item in unread.json()["data"]["results"]], [own_unread.id])
        self.assertEqual(count.json()["data"], {"خوانده نشده ها": 1})

        mark_one = self.client.post(
            f"/api/v1/notifications/notif/{own_unread.id}/mark_as_read/",
            **auth_headers(self.user),
        )
        mark_all = self.client.post(
            "/api/v1/notifications/notif/mark_all_read/",
            **auth_headers(self.user),
        )
        self.assertEqual(mark_one.status_code, 200)
        self.assertEqual(mark_all.status_code, 200)
        own_unread.refresh_from_db()
        own_read.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(own_unread.is_read)
        self.assertTrue(own_read.is_read)
        self.assertFalse(other.is_read)
        delay.assert_not_called()

    def test_notification_and_fcm_routes_require_authentication(self):
        self.assertEqual(self.client.get("/api/v1/notifications/notif/").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/notifications/fcm-token/", {"token": "x"}).status_code, 401)

    def test_other_users_notification_cannot_be_marked_read(self):
        notification = UserNotification.objects.create(
            user=self.other_user,
            title="Private",
            description="Private",
        )
        response = self.client.post(
            f"/api/v1/notifications/notif/{notification.id}/mark_as_read/",
            **auth_headers(self.user),
        )
        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_fcm_registration_requires_token_and_updates_token_owner(self):
        empty = self.client.post(
            "/api/v1/notifications/fcm-token/",
            {"token": ""},
            content_type="application/json",
            **auth_headers(self.user),
        )
        self.assertEqual(empty.status_code, 400)

        saved = self.client.post(
            "/api/v1/notifications/fcm-token/",
            {"token": "shared-token"},
            content_type="application/json",
            **auth_headers(self.user),
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(UserFCMToken.objects.get(token="shared-token").user_id, self.user.id)

        moved = self.client.post(
            "/api/v1/notifications/fcm-token/",
            {"token": "shared-token"},
            content_type="application/json",
            **auth_headers(self.other_user),
        )
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(UserFCMToken.objects.get(token="shared-token").user_id, self.other_user.id)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "notification-task-tests",
        }
    }
)
class FirebaseTaskTests(TestCase):
    def setUp(self):
        self.user = create_user("firebase-task@example.com")

    @patch("Notification.tasks.messaging.send", return_value="message-id")
    @patch("Notification.tasks.messaging.Message")
    @patch("Notification.tasks.get_firebase_app", return_value=object())
    def test_firebase_task_builds_and_sends_message(self, get_app, message, send):
        result = send_firebase_task.run({
            "fcm": "token",
            "title": "Title",
            "message": "Body",
            "notification_id": 12,
            "enabled": True,
        })
        self.assertEqual(result, {"success": True, "message_id": "message-id"})
        get_app.assert_called_once_with()
        message.assert_called_once()
        send.assert_called_once_with(message.return_value, app=get_app.return_value)
        kwargs = message.call_args.kwargs
        self.assertEqual(kwargs["token"], "token")
        self.assertEqual(kwargs["notification"].title, "Title")
        self.assertEqual(kwargs["notification"].body, "Body")
        self.assertEqual(kwargs["data"], {"notification_id": "12", "enabled": "True"})

    @patch("Notification.tasks.messaging.send")
    @patch("Notification.tasks.get_firebase_app", return_value=object())
    def test_unregistered_token_is_deleted(self, get_app, send):
        token = UserFCMToken.objects.create(user=self.user, token="dead-token")
        send.side_effect = __import__("firebase_admin").messaging.UnregisteredError("gone")
        result = send_firebase_task.run({"fcm": token.token, "title": "Title", "message": "Body"})
        self.assertEqual(result, {"success": False, "error": "unregistered"})
        self.assertFalse(UserFCMToken.objects.filter(pk=token.pk).exists())

    @patch("Notification.tasks.messaging.send", side_effect=RuntimeError("firebase down"))
    @patch("Notification.tasks.get_firebase_app", return_value=object())
    def test_generic_firebase_failure_retries(self, get_app, send):
        with patch.object(send_firebase_task, "retry", side_effect=RuntimeError("retry")) as retry:
            with self.assertRaises(RuntimeError):
                send_firebase_task.run({"fcm": "token", "title": "Title", "message": "Body"})
        retry.assert_called_once()
