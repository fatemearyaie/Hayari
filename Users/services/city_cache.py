from django.core.cache import cache
from Users.models.users_models import City
from Users.serializers.users_serializers import CitySerializer


CITIES_CACHE_TTL = 60 * 60 * 24
CACHE_KEY = "city:all"

def get_cached_cities():
    data = cache.get(CACHE_KEY)
    if data is None:
        qs = City.objects.filter(is_available=True).only("id", "name")
        data = CitySerializer(qs, many=True).data
        cache.set(CACHE_KEY, data, CITIES_CACHE_TTL)
    return data