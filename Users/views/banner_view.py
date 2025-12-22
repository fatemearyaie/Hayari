from requests import Response
from rest_framework.views import APIView

from Users.services.banner_cache import get_cached_banners


class BannerView(APIView):
    throttle_scope = 'custom'
    def get(self, request):
        banners = get_cached_banners()
        return Response(banners)