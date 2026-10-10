"""Cache hit/miss and JWT lookup; use local memory rather than Redis."""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from Users.models.banner_models import HomeBanner
from Users.models.users_models import City, Country, CustomUser
from Users.services.banner_cache import BANNER_CACHE_KEY, BANNER_CACHE_TTL, get_cached_banners
from Users.services.city_cache import CACHE_KEY, CITIES_CACHE_TTL, get_cached_cities
from Users.services.token_cache import CacheJWTAuthentication


LOCAL_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCAL_CACHES)
class CityCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_hit_returns_cached_value(self):
        cache.set(CACHE_KEY, [{"id": 11, "name": "From cache"}])
        with patch("Users.services.city_cache.City.objects.filter") as query:
            result = get_cached_cities()
        self.assertEqual(result, [{"id": 11, "name": "From cache"}])
        query.assert_not_called()

    def test_miss_loads_only_available_cities_and_caches_result(self):
        country = Country.objects.create(name="Country")
        City.objects.create(name="Visible", country=country, is_available=True)
        City.objects.create(name="Hidden", country=country, is_available=False)
        cache.clear()
        result = get_cached_cities()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Visible")
        self.assertEqual(cache.get(CACHE_KEY), result)
        self.assertEqual(CITIES_CACHE_TTL, 86400)


@override_settings(CACHES=LOCAL_CACHES)
class BannerCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_hit_avoids_database_query(self):
        cache.set(BANNER_CACHE_KEY, [{"message": "Cached"}])
        with patch("Users.services.banner_cache.HomeBanner.objects.filter") as query:
            result = get_cached_banners()
        self.assertEqual(result, [{"message": "Cached"}])
        query.assert_not_called()

    def test_miss_caches_serialized_active_home_banners(self):
        HomeBanner.objects.create(
            banner="banners/home/visible.jpg", message="Visible", url="https://example.com"
        )
        result = get_cached_banners()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["message"], "Visible")
        self.assertEqual(cache.get(BANNER_CACHE_KEY), result)
        self.assertEqual(BANNER_CACHE_TTL, 86400)


@override_settings(CACHES=LOCAL_CACHES)
class JWTUserCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = CustomUser.objects.create_user(phone="09125551110")
        self.claims = {"user_id": self.user.pk}

    def test_first_lookup_loads_from_db_then_populates_cache(self):
        actual = CacheJWTAuthentication().get_user(self.claims)
        self.assertEqual(actual.pk, self.user.pk)
        self.assertEqual(cache.get(f"user:obj:{self.user.pk}").pk, self.user.pk)

    def test_cache_hit_does_not_use_database(self):
        cache.set(f"user:obj:{self.user.pk}", self.user)
        with patch("rest_framework_simplejwt.authentication.JWTAuthentication.get_user") as lookup:
            actual = CacheJWTAuthentication().get_user(self.claims)
        self.assertEqual(actual.pk, self.user.pk)
        lookup.assert_not_called()

    def test_missing_user_id_claim_is_rejected(self):
        from rest_framework.exceptions import AuthenticationFailed

        with self.assertRaises(AuthenticationFailed):
            CacheJWTAuthentication().get_user({})
