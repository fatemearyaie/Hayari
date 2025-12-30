from django.urls import path

from Lottery.views.lottery_views import ActiveLotteryView

urlpatterns =[
    path('active/', ActiveLotteryView.as_view(), name='active-lottery'),
]