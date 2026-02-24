from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from Users.views.banner_view import HomeBannerView, SplashView
from Users.views.transactions_views import TransactionView, PaymentViewSet
from Users.views.users_views import OTPGeneratorView, OTPVerifyView, UserProfileView, CityView, GoogleAuthView

router = DefaultRouter()
router.register(r'zarinpal', PaymentViewSet, basename='zarinpal')
router.register(r'transactions', TransactionView, basename='transaction')
router.register(r'home/banner', HomeBannerView, basename='home')

urlpatterns =[
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('auth/', OTPGeneratorView.as_view(), name='auth'),
    path('auth/register/', OTPVerifyView.as_view(), name='auth-register'),
    path('cities/', CityView.as_view(), name='city-list'),
    path('splash/', SplashView.as_view(),name='splash'),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('auth/google/', GoogleAuthView.as_view(), name='auth'),
]
urlpatterns += router.urls