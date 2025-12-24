from rest_framework.routers import DefaultRouter
from Ads.views.ads_views import AdSettingView, AdCategoryView

router = DefaultRouter()
router.register(r'ad/settings', AdSettingView, basename='ad-setting')
router.register(r'ad/category', AdCategoryView, basename='ad-category')

urlpatterns = router.urls
