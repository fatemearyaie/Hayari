from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Funds.views.funds_views import FundRaisingGV, DonateGV, MyDonationAnayticsView

router = DefaultRouter()
router.register(r'fundraisings', FundRaisingGV, basename='fundraising')
router.register(r'donation',DonateGV, basename='donate')
router.register(r'analytics',MyDonationAnayticsView, basename='donation-analytics')
urlpatterns = [
]
urlpatterns += router.urls