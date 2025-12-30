from rest_framework import serializers
from Lottery.models.lottery_models import LotteryRewards, Lottery
from Users.serializers.users_serializers import OtherUserProfileSerializer


class ActiveLotterySerializer(serializers.ModelSerializer):
    class Meta:
        model = Lottery
        fields = ['name','description','lottery_datetime']
        

class LotteryRewardSerializer(serializers.ModelSerializer):
    user = OtherUserProfileSerializer()
    lottery = ActiveLotterySerializer(read_only=True)
    class Meta:
        model = LotteryRewards
        fields = ("lottery","user","place","amount",)

class LotteryWinnersSerializer(serializers.ModelSerializer):
    winners = LotteryRewardSerializer(source="lotteryrewards_set", many=True, read_only=True)
    class Meta:
        model = Lottery
        fields = ("name","lottery_datetime","winners",)