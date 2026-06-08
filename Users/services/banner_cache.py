from django.core.cache import cache
from Users.models.banner_models import HomeBanner
from Users.serializers.banner_serializers import HomeBannerSerializer

BANNER_CACHE_TTL = 60 * 60 * 24
BANNER_CACHE_KEY = "banner:active"


def get_cached_banners():
    data = cache.get(BANNER_CACHE_KEY)
    if data is None:
        banners = HomeBanner.objects.filter(is_active=True)
        data = HomeBannerSerializer(banners, many=True).data
        cache.set(BANNER_CACHE_KEY, data, BANNER_CACHE_TTL)
    return data
