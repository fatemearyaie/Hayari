from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Funds.views.funds_views import FundRaisingView, DonateView

router = DefaultRouter()
router.register(r'fundraisings', FundRaisingView, basename='fundraising')
router.register(r'donation',DonateView, basename='donate')
urlpatterns = [
]
urlpatterns += router.urls