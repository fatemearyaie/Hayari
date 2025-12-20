from django.urls import path

from Users.views.users_views import OTPGeneratorView, OTPVerifyView

urlpatterns =[
    path('auth/', OTPGeneratorView.as_view(), name='auth'),
    path('auth/register/', OTPVerifyView.as_view(), name='auth-register'),
]