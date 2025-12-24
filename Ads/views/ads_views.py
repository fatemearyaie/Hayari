from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from Ads.models.ads_models import AdSetting, AdCategory
from Ads.serializers.ads_serializers import AdSettingSerializer, AdCategorySerializer


# Create your views here.

class AdSettingView(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AdSettingSerializer


    filter_backends = [DjangoFilterBackend,SearchFilter,OrderingFilter,]
    filterset_fields = ['is_available']
    search_fields = ['video_xp', 'banner_xp']
    ordering_fields = ['video_price', 'banner_price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return (AdSetting.objects.filter(is_available=True))


class AdCategoryView(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AdCategorySerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter, ]
    filterset_fields = ['is_available']
    search_fields = ['name']
    ordering_fields = ['name','created_at']
    ordering = ['name']

    def get_queryset(self):
        return (AdCategory.objects.filter(is_available=True))