from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from Lottery.models.lottery_models import Lottery, LotteryRewards
from Lottery.serializers.lottery_serializers import ActiveLotterySerializer, LotteryWinnersSerializer, \
    LotteryRewardSerializer, LastLotteryUserStatusSerializer


# Create your views here.
class ActiveLotteryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        queryset = Lottery.objects.prefetch_related('lotteryrewards_set').get(is_active=True)
        serializer = ActiveLotterySerializer(queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PreviousLotteryWinnersView(ReadOnlyModelViewSet):
    serializer_class = LotteryRewardSerializer
    throttle_scope = 'custom'
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["place", "amount"]
    ordering_fields = ["place", "amount"]

    def get_queryset(self):
        lottery = (Lottery.objects.filter(is_active=False).order_by("-lottery_datetime", "-id").first())
        if not lottery:
            return LotteryRewards.objects.none()

        return (LotteryRewards.objects.filter(lottery=lottery, user__isnull=False).select_related("user", "lottery").order_by("place", "-amount", "id"))


class LastLotteryUserStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        last_lottery = Lottery.objects.order_by("-lottery_datetime", "-id").first()
        if not last_lottery:
            return Response({"اخطار": "لاتاری پیدا نشد"}, status=status.HTTP_404_NOT_FOUND)
        reward = (LotteryRewards.objects.select_related('user').filter(lottery=last_lottery, user=request.user).first())
        data = {
            "lottery": last_lottery,
            "status": "win" if reward else "not_win",
            "reward": reward,
        }
        serializer = LastLotteryUserStatusSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)