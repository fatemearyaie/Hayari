from rest_framework.routers import DefaultRouter
from Ads.views.ads_views import AdSettingViewSet, AdCategoryViewSet, AdvertisementViewSet, AllAdvertisementViewSet

router = DefaultRouter()
router.register(r'settings', AdSettingViewSet, basename='ad-setting')
router.register(r'category', AdCategoryViewSet, basename='ad-category')
router.register(r'advertisement', AdvertisementViewSet, basename='advertisement')
router.register(r'alladvertisements', AllAdvertisementViewSet, basename='advertisement-all')

urlpatterns = router.urls
