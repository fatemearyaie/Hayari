from rest_framework.routers import DefaultRouter
from Ads.views.ads_views import AdSettingView

router = DefaultRouter()
router.register(r'ad/settings', AdSettingView, basename='ad-setting')

urlpatterns = router.urls
