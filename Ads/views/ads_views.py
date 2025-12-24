from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from Ads.models.ads_models import AdSetting, AdCategory, Advertisement
from Ads.serializers.ads_serializers import AdSettingSerializer, AdCategorySerializer, CreateAdvertisementSerializer, \
    UpdateAdvertisementSerializer, AdvertisementReadSerializer


# Create your views here.

class AdSettingViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AdSettingSerializer


    filter_backends = [DjangoFilterBackend,SearchFilter,OrderingFilter,]
    filterset_fields = ['is_available']
    search_fields = ['video_xp', 'banner_xp']
    ordering_fields = ['video_price', 'banner_price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return (AdSetting.objects.filter(is_available=True))


class AdCategoryViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AdCategorySerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter, ]
    filterset_fields = ['is_available']
    search_fields = ['name']
    ordering_fields = ['name','created_at']
    ordering = ['name']

    def get_queryset(self):
        return (AdCategory.objects.filter(is_available=True))

class AdvertisementViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]


    def get_serializer_class(self):
        if self.action == 'create':  # POST
            return CreateAdvertisementSerializer

        if self.action in ['update', 'partial_update']:  # PUT / PATCH
            return UpdateAdvertisementSerializer
        return AdvertisementReadSerializer


    def get_queryset(self):
        return Advertisement.objects.filter(user=self.request.user).order_by('-created_at')

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed('DELETE')