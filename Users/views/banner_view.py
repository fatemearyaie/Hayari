from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from Users.models.banner_models import HomeBanner
from Users.serializers.banner_serializers import HomeBannerSerializer
from Users.services.banner_cache import get_cached_banners


class BannerView(APIView):
    throttle_scope = 'custom'
    def get(self, request):
        banners = get_cached_banners()
        return Response(banners)


class HomeBannerView(APIView):
    def get(self, request):
        banner = HomeBanner.objects.order_by('-created_at').first()
        if not banner:
            return Response(
                {"detail": "No banner available"},
                status=status.HTTP_204_NO_CONTENT
            )
        serializer = HomeBannerSerializer(banner)
        return Response(serializer.data)



class SplashView(APIView):
    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response('you are not authenticate',status=status.HTTP_403_FORBIDDEN)
        return Response('welcome!',status=status.HTTP_200_OK)