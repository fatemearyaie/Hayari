from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Funds.views.funds_views import FundRaisingView

router = DefaultRouter()
router.register(r'fundraisings', FundRaisingView, basename='fundraising')

urlpatterns = [
]
urlpatterns += router.urls