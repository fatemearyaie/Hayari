from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from Users.models.banner_models import HomeBanner, LoginEntry
from Users.serializers.banner_serializers import HomeBannerSerializer
from Users.services.banner_cache import get_cached_banners


class BannerView(APIView):
    throttle_scope = 'custom'
    def get(self, request):
        banners = get_cached_banners()
        return Response(banners)


class HomeBannerView(ReadOnlyModelViewSet):
    queryset = HomeBanner.objects.all()
    serializer_class = HomeBannerSerializer



class SplashView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        LoginEntry.objects.create(user_id=request.user.id)
        return Response('welcome!',status=status.HTTP_200_OK)