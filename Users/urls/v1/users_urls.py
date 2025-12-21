from django.urls import path

from Users.views.users_views import OTPGeneratorView, OTPVerifyView, UserProfileView

urlpatterns =[
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('auth/', OTPGeneratorView.as_view(), name='auth'),
    path('auth/register/', OTPVerifyView.as_view(), name='auth-register'),
]