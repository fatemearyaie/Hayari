from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from Lottery.models.lottery_models import Lottery, LotteryRewards
from Lottery.serializers.lottery_serializers import ActiveLotterySerializer, LotteryWinnersSerializer, \
    LotteryRewardSerializer


# Create your views here.
class ActiveLotteryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        queryset = Lottery.objects.get(is_active=True)
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