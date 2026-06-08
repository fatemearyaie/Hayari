from rest_framework.routers import DefaultRouter
from Ads.views.ads_views import AdSettingViewAPIView, AdCategoryViewSet, AdvertisementViewSet, AllAdvertisementViewSet
from django.urls import path
router = DefaultRouter()
# router.register(r'settings', AdSettingViewAPIView, basename='ad-setting')
router.register(r'category', AdCategoryViewSet, basename='ad-category')
router.register(r'advertisement', AdvertisementViewSet, basename='advertisement')
router.register(r'alladvertisements', AllAdvertisementViewSet, basename='advertisement-all')
urlpatterns = [
    path("settings/", AdSettingViewAPIView.as_view(), name="ad-setting"),
]
urlpatterns += router.urls
