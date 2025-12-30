from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from Ads.models.ads_models import AdSetting, AdCategory, Advertisement
from Ads.serializers.ads_serializers import AdSettingSerializer, AdCategorySerializer, CreateAdvertisementSerializer, \
    UpdateAdvertisementSerializer, AdvertisementReadSerializer, MyAdvertisementSerializer, AdEventSerializer


# Create your views here.


class AdSettingViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        setting = AdSetting.objects.get(is_available=True)
        serializer = AdSettingSerializer(setting)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdCategoryViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AdCategorySerializer
    pagination_class = None

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
        return MyAdvertisementSerializer

    def get_queryset(self):
        return Advertisement.objects.filter(user=self.request.user).order_by('-created_at').select_related('user','category','city')

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed('DELETE')

    @action(detail=True, methods=['post'], url_path='event')
    def event(self, request, pk=None):
        ad = get_object_or_404(
            Advertisement.objects.select_related('category', 'city'),
            pk=pk,
            status=Advertisement.AdStatus.Enable
        )

        serializer = AdEventSerializer(
            data=request.data,
            context={'request': request, 'ad': ad}
        )
        serializer.is_valid(raise_exception=True)
        event_obj = serializer.save()

        return Response(AdEventSerializer(event_obj).data)


class AllAdvertisementViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AdvertisementReadSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter, ]
    filterset_fields = ['category','created_at','city']
    search_fields = ['title','category','city']
    ordering_fields = ['created_at', 'title','city']
    ordering = ['created_at']

    def get_queryset(self):
        return Advertisement.objects.filter(status=Advertisement.AdStatus.Enable).order_by('-created_at').select_related('city','user','category')


