from django.urls import path
from rest_framework.routers import DefaultRouter

from Users.views.transactions_views import TransactionView, PaymentViewSet
from Users.views.users_views import OTPGeneratorView, OTPVerifyView, UserProfileView

router = DefaultRouter()
router.register(r'zarinpal', PaymentViewSet, basename='zarinpal')
router.register(r'transactions', TransactionView, basename='transaction')


urlpatterns =[
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('auth/', OTPGeneratorView.as_view(), name='auth'),
    path('auth/register/', OTPVerifyView.as_view(), name='auth-register'),
]
urlpatterns += router.urls