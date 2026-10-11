from decimal import Decimal
from base64 import b64decode
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import AccessToken

from Ads.models.ads_models import AdCategory, AdEvent, AdSetting, Advertisement
from Ads.serializers.ads_serializers import (
    AdCategorySerializer,
    AdEventSerializer,
    AdSettingSerializer,
    CreateAdvertisementSerializer,
)
from Ads.services.video_duration import (
    VideoDurationError,
    get_duration_bucket,
    get_video_duration_seconds,
    get_video_duration_seconds_from_path,
)
from Users.models import City, Country, CustomUser, Transaction, XPTracker


VALID_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def create_user(email, balance=Decimal("0")):
    return CustomUser.objects.create_user(email=email, balance=balance)


def create_city(name="Tehran"):
    country = Country.objects.create(name=f"Country {name}")
    return City.objects.create(name=name, country=country, is_available=True)


def auth_headers(user):
    token = AccessToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def request_for(user):
    return SimpleNamespace(user=user)


def image_file(name="ad.png"):
    return SimpleUploadedFile(name, VALID_PNG, content_type="image/png")


def video_file(name="ad.mp4"):
    return SimpleUploadedFile(name, b"video-data", content_type="video/mp4")


def advertisement_data(city_id, category_id, **media):
    data = {
        "city": city_id,
        "category": category_id,
        "title": "Test advertisement",
    }
    data.update(media)
    return data


class VideoDurationTests(SimpleTestCase):
    def test_duration_bucket_boundaries(self):
        self.assertEqual(get_duration_bucket(30), 30)
        self.assertEqual(get_duration_bucket(31.4), 30)
        self.assertEqual(get_duration_bucket(31.6), 60)
        self.assertEqual(get_duration_bucket(60), 60)
        self.assertEqual(get_duration_bucket(91.4), 90)
        self.assertEqual(get_duration_bucket(121.5), 120)
        with self.assertRaises(VideoDurationError):
            get_duration_bucket(121.6)

    def test_video_duration_from_uploaded_file_uses_ffprobe(self):
        uploaded = SimpleUploadedFile("video.mp4", b"video-data")
        result = Mock(returncode=0, stdout='{"format": {"duration": "61.25"}}')
        with patch("Ads.services.video_duration.subprocess.run", return_value=result) as run:
            self.assertEqual(get_video_duration_seconds(uploaded), 61.25)
        run.assert_called_once()

    def test_video_duration_from_path_rejects_probe_failures(self):
        for result in (
            Mock(returncode=1, stdout=""),
            Mock(returncode=0, stdout=""),
            Mock(returncode=0, stdout="not-json"),
        ):
            with patch("Ads.services.video_duration.subprocess.run", return_value=result):
                with self.assertRaises(VideoDurationError):
                    get_video_duration_seconds_from_path("video.mp4")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ads-tests",
        }
    }
)
class AdsModelAndSerializerTests(TestCase):
    def setUp(self):
        self.media_dir = __import__("tempfile").TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_dir.cleanup)
        self.user = create_user("ads-owner@example.com", balance=Decimal("1000"))
        self.city = create_city()
        self.category = AdCategory.objects.create(name="Technology")
        self.setting = AdSetting.objects.create(
            video_price_30=30,
            video_price_60=60,
            video_price_90=90,
            video_price_120=120,
            video_xp=9,
            banner_price=25,
            banner_xp=4,
        )

    def test_available_ad_setting_replaces_previous_available_setting(self):
        previous = self.setting
        second = AdSetting.objects.create(
            video_price_30=31,
            video_price_60=61,
            video_price_90=91,
            video_price_120=121,
            video_xp=10,
            banner_price=26,
            banner_xp=5,
        )
        previous.refresh_from_db()
        self.assertFalse(previous.is_available)
        self.assertTrue(second.is_available)

    def test_setting_and_category_serializers_expose_current_fields(self):
        setting_data = AdSettingSerializer(self.setting).data
        category_data = AdCategorySerializer(self.category).data
        self.assertEqual(set(setting_data), {
            "video_price_30",
            "video_price_60",
            "video_price_90",
            "video_price_120",
            "video_xp",
            "banner_price",
            "banner_xp",
            "is_available",
        })
        self.assertEqual(category_data["name"], "Technology")
        self.assertEqual(category_data["id"], self.category.id)

    def test_creation_requires_authentication_and_active_settings(self):
        unauthenticated = CreateAdvertisementSerializer(
            data=advertisement_data(self.city.id, self.category.id, image=image_file())
        )
        self.assertFalse(unauthenticated.is_valid())

        AdSetting.objects.all().update(is_available=False)
        no_setting = CreateAdvertisementSerializer(
            data=advertisement_data(self.city.id, self.category.id, image=image_file()),
            context={"request": request_for(self.user)},
        )
        self.assertFalse(no_setting.is_valid())
        self.assertIn("تنظیمات", no_setting.errors)

    def test_creation_rejects_missing_or_multiple_media(self):
        missing = CreateAdvertisementSerializer(
            data=advertisement_data(self.city.id, self.category.id),
            context={"request": request_for(self.user)},
        )
        both = CreateAdvertisementSerializer(
            data=advertisement_data(
                self.city.id,
                self.category.id,
                image=image_file(),
                video=video_file(),
            ),
            context={"request": request_for(self.user)},
        )
        self.assertFalse(missing.is_valid())
        self.assertFalse(both.is_valid())
        self.assertIn("فایل", missing.errors)
        self.assertIn("فایل", both.errors)

    @patch("Ads.serializers.ads_serializers.get_video_duration_seconds")
    def test_video_validation_maps_duration_to_configured_price(self, get_duration):
        get_duration.return_value = 61
        serializer = CreateAdvertisementSerializer(
            data=advertisement_data(self.city.id, self.category.id, video=video_file()),
            context={"request": request_for(self.user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["calculated_price"], Decimal("60"))
        self.assertEqual(serializer.validated_data["video_bucket"], 60)

    @patch("Ads.serializers.ads_serializers.get_video_duration_seconds")
    def test_video_duration_error_is_returned_as_validation_error(self, get_duration):
        get_duration.side_effect = VideoDurationError("duration failure")
        serializer = CreateAdvertisementSerializer(
            data=advertisement_data(self.city.id, self.category.id, video=video_file()),
            context={"request": request_for(self.user)},
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["ویدیو"][0], "duration failure")

    def test_missing_video_bucket_price_is_rejected(self):
        setting = SimpleNamespace(
            banner_price=25,
            video_price_30=30,
            video_price_60=60,
            video_price_90=None,
            video_price_120=120,
        )
        with patch("Ads.serializers.ads_serializers.AdSetting.objects.filter") as filter_settings:
            filter_settings.return_value.first.return_value = setting
            with patch("Ads.serializers.ads_serializers.get_video_duration_seconds", return_value=91):
                serializer = CreateAdvertisementSerializer(
                    data=advertisement_data(self.city.id, self.category.id, video=video_file()),
                    context={"request": request_for(self.user)},
                )
        self.assertFalse(serializer.is_valid())
        self.assertIn("ویدیو", serializer.errors)

    def test_creation_charges_balance_and_records_transaction(self):
        serializer = CreateAdvertisementSerializer(
            data=advertisement_data(self.city.id, self.category.id, image=image_file()),
            context={"request": request_for(self.user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        advertisement = serializer.save()
        self.user.refresh_from_db()
        self.assertEqual(advertisement.user_id, self.user.id)
        self.assertEqual(self.user.balance, Decimal("975"))
        transaction = Transaction.objects.get(user=self.user)
        self.assertEqual(transaction.amount, Decimal("25"))
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.Withdraw)
        self.assertEqual(transaction.transaction_status, Transaction.TransactionStatus.COMPLETE)

    def test_creation_rolls_back_when_balance_is_insufficient(self):
        self.user.balance = 10
        self.user.save(update_fields=["balance"])
        serializer = CreateAdvertisementSerializer(
            data=advertisement_data(self.city.id, self.category.id, image=image_file()),
            context={"request": request_for(self.user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ValidationError):
            serializer.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("10"))
        self.assertFalse(Advertisement.objects.exists())
        self.assertFalse(Transaction.objects.filter(user=self.user).exists())

    def test_event_records_counter_and_xp_once_per_day(self):
        advertisement = Advertisement.objects.create(
            user=self.user,
            city=self.city,
            category=self.category,
            title="Visible ad",
            image=image_file(),
            status=Advertisement.AdStatus.Enable,
        )
        actor = create_user("ads-viewer@example.com")
        serializer = AdEventSerializer(
            data={"event_type": AdEvent.EventType.View},
            context={"request": request_for(actor), "ad": advertisement},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()
        advertisement.refresh_from_db()
        self.assertEqual(event.event_type, AdEvent.EventType.View)
        self.assertEqual(advertisement.total_view, 1)
        self.assertEqual(advertisement.total_click, 0)
        self.assertEqual(XPTracker.objects.filter(user=actor, reason=XPTracker.Reason.Ads).count(), 1)
        self.assertEqual(XPTracker.objects.get(user=actor).xp, 4)

        event.save()
        self.assertEqual(XPTracker.objects.filter(user=actor, reason=XPTracker.Reason.Ads).count(), 1)

        duplicate = AdEventSerializer(
            data={"event_type": AdEvent.EventType.Click},
            context={"request": request_for(actor), "ad": advertisement},
        )
        self.assertTrue(duplicate.is_valid(), duplicate.errors)
        with self.assertRaises(ValidationError):
            duplicate.save()
        self.assertEqual(AdEvent.objects.filter(user=actor, ad=advertisement).count(), 1)

    def test_event_requires_request_and_ad_context(self):
        no_request = AdEventSerializer(data={"event_type": AdEvent.EventType.View})
        no_ad = AdEventSerializer(
            data={"event_type": AdEvent.EventType.View},
            context={"request": request_for(self.user)},
        )
        self.assertFalse(no_request.is_valid())
        self.assertFalse(no_ad.is_valid())

    def test_event_xp_uses_video_setting_and_zero_xp_is_ignored(self):
        advertisement = Advertisement.objects.create(
            user=self.user,
            city=self.city,
            category=self.category,
            title="Video ad",
            video=video_file(),
            status=Advertisement.AdStatus.Enable,
        )
        actor = create_user("ads-video-viewer@example.com")
        AdEvent.objects.create(user=actor, ad=advertisement, event_type=AdEvent.EventType.Click)
        self.assertEqual(XPTracker.objects.get(user=actor).xp, 9)

        AdSetting.objects.filter(pk=self.setting.pk).update(video_xp=0)
        second_actor = create_user("ads-zero-xp@example.com")
        AdEvent.objects.create(user=second_actor, ad=advertisement, event_type=AdEvent.EventType.View)
        self.assertFalse(XPTracker.objects.filter(user=second_actor).exists())


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ads-http-tests",
        }
    }
)
class AdsRefundAndHttpTests(TestCase):
    def setUp(self):
        self.user = create_user("ads-http-owner@example.com", balance=Decimal("1000"))
        self.other_user = create_user("ads-http-other@example.com", balance=Decimal("1000"))
        self.city = create_city("Shiraz")
        self.category = AdCategory.objects.create(name="News")
        self.other_category = AdCategory.objects.create(name="Games", is_available=False)
        self.setting = AdSetting.objects.create(
            video_price_30=30,
            video_price_60=60,
            video_price_90=90,
            video_price_120=120,
            video_xp=8,
            banner_price=40,
            banner_xp=3,
        )
        self.client = Client()
        self.media_dir = __import__("tempfile").TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_dir.cleanup)

    def create_ad(self, **kwargs):
        values = {
            "user": self.user,
            "city": self.city,
            "category": self.category,
            "title": "Advertisement",
            "image": image_file(),
            "status": Advertisement.AdStatus.Pending,
        }
        values.update(kwargs)
        return Advertisement.objects.create(**values)

    def test_image_rejection_refund_is_idempotent(self):
        advertisement = self.create_ad()
        advertisement.status = Advertisement.AdStatus.Rejected
        advertisement.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("1040"))
        self.assertEqual(Transaction.objects.filter(description=f"refund_ad:{advertisement.id}").count(), 1)

        advertisement.save()
        self.assertEqual(Transaction.objects.filter(description=f"refund_ad:{advertisement.id}").count(), 1)

    def test_rejection_without_ad_settings_does_not_refund(self):
        advertisement = self.create_ad()
        AdSetting.objects.all().delete()
        advertisement.status = Advertisement.AdStatus.Rejected
        advertisement.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("1000"))
        self.assertFalse(Transaction.objects.filter(description__startswith="refund_ad:").exists())

    @patch("Ads.signals.refund_signal.get_video_duration_seconds_from_path", return_value=61)
    def test_video_rejection_refund_uses_duration_bucket(self, get_duration):
        advertisement = self.create_ad(image=None, video=video_file())
        advertisement.status = Advertisement.AdStatus.Rejected
        advertisement.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("1060"))
        get_duration.assert_called_once()

    @patch("Ads.signals.refund_signal.get_video_duration_seconds_from_path", side_effect=VideoDurationError("bad"))
    def test_unsupported_video_duration_does_not_refund(self, get_duration):
        advertisement = self.create_ad(image=None, video=video_file())
        advertisement.status = Advertisement.AdStatus.Rejected
        advertisement.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("1000"))
        self.assertFalse(Transaction.objects.filter(description__startswith="refund_ad:").exists())

    def test_non_rejected_transition_does_not_refund(self):
        advertisement = self.create_ad()
        advertisement.status = Advertisement.AdStatus.Enable
        advertisement.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("1000"))
        self.assertFalse(Transaction.objects.filter(description__startswith="refund_ad:").exists())

    def test_settings_and_categories_require_authentication(self):
        self.assertEqual(self.client.get("/api/v1/ads/settings/").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/ads/category/").status_code, 401)

        settings_response = self.client.get("/api/v1/ads/settings/", **auth_headers(self.user))
        self.assertEqual(settings_response.status_code, 200)
        self.assertEqual(str(settings_response.json()["data"]["banner_price"]), "40")
        self.assertTrue(settings_response.json()["data"]["is_available"])

        response = self.client.get("/api/v1/ads/category/", **auth_headers(self.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()["data"]], ["News"])

    def test_category_search_and_ordering_use_available_categories(self):
        AdCategory.objects.create(name="Books")
        response = self.client.get(
            "/api/v1/ads/category/?search=bo&ordering=name",
            **auth_headers(self.user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()["data"]], ["Books"])

    def test_owned_advertisement_list_and_update_are_scoped_to_user(self):
        own = self.create_ad(title="Own")
        other = self.create_ad(user=self.other_user, title="Other")
        response = self.client.get("/api/v1/ads/advertisement/", **auth_headers(self.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["data"]["results"]], [own.id])

        other_detail = self.client.get(
            f"/api/v1/ads/advertisement/{other.id}/",
            **auth_headers(self.user),
        )
        self.assertEqual(other_detail.status_code, 404)

        created = self.client.post(
            "/api/v1/ads/advertisement/",
            {
                "city": self.city.id,
                "category": self.category.id,
                "title": "Created through HTTP",
                "image": image_file("http-ad.png"),
            },
            **auth_headers(self.user),
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(Advertisement.objects.filter(title="Created through HTTP", user=self.user).exists())

        update = self.client.patch(
            f"/api/v1/ads/advertisement/{own.id}/",
            {"title": "Updated"},
            content_type="application/json",
            **auth_headers(self.user),
        )
        self.assertEqual(update.status_code, 200)
        own.refresh_from_db()
        self.assertEqual(own.title, "Updated")

        delete = self.client.delete(
            f"/api/v1/ads/advertisement/{own.id}/",
            **auth_headers(self.user),
        )
        self.assertEqual(delete.status_code, 405)

    def test_all_advertisements_exclude_ads_already_seen_today(self):
        visible = self.create_ad(user=self.other_user, title="Visible", status=Advertisement.AdStatus.Enable)
        seen = self.create_ad(user=self.other_user, title="Seen", status=Advertisement.AdStatus.Enable)
        AdEvent.objects.create(
            user=self.user,
            ad=seen,
            event_type=AdEvent.EventType.View,
            event_date=timezone.localdate(),
        )
        response = self.client.get("/api/v1/ads/alladvertisements/", **auth_headers(self.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["data"]["results"]], [visible.id])

    def test_event_endpoint_requires_enabled_ad_and_updates_counter(self):
        advertisement = self.create_ad(user=self.other_user, status=Advertisement.AdStatus.Enable)
        unauthenticated = self.client.post(
            f"/api/v1/ads/advertisement/{advertisement.id}/event/",
            {"event_type": "click"},
            content_type="application/json",
        )
        self.assertEqual(unauthenticated.status_code, 401)

        response = self.client.post(
            f"/api/v1/ads/advertisement/{advertisement.id}/event/",
            {"event_type": "click"},
            content_type="application/json",
            **auth_headers(self.user),
        )
        self.assertEqual(response.status_code, 200)
        advertisement.refresh_from_db()
        self.assertEqual(advertisement.total_click, 1)

        advertisement.status = Advertisement.AdStatus.Disable
        advertisement.save(update_fields=["status"])
        unavailable = self.client.post(
            f"/api/v1/ads/advertisement/{advertisement.id}/event/",
            {"event_type": "view"},
            content_type="application/json",
            **auth_headers(self.user),
        )
        self.assertEqual(unavailable.status_code, 404)
