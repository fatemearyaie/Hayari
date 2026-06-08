
from django.urls import path
from rest_framework.routers import DefaultRouter
from Lottery.views.lottery_views import ActiveLotteryView, PreviousLotteryWinnersView, LastLotteryUserStatusView

router = DefaultRouter()
router.register(r"previous/winners", PreviousLotteryWinnersView, basename="previous-lottery-winners")

urlpatterns =[
    path('active/', ActiveLotteryView.as_view(), name='active-lottery'),
    path("status/",LastLotteryUserStatusView.as_view(),name="last-lottery-user-status"),
]
urlpatterns += router.urls