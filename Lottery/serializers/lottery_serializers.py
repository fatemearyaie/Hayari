from rest_framework import serializers
from Lottery.models.lottery_models import LotteryRewards, Lottery

class ActiveLotterySerializer(serializers.ModelSerializer):
    class Meta:
        model = Lottery
        fields = ['name','description','lottery_datetime']
