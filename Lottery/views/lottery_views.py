from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Lottery.models.lottery_models import Lottery
from Lottery.serializers.lottery_serializers import ActiveLotterySerializer


# Create your views here.
class ActiveLotteryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        queryset = Lottery.objects.get(is_active=True)
        serializer = ActiveLotterySerializer(queryset)
        return Response(serializer.data, status=status.HTTP_200_OK)
