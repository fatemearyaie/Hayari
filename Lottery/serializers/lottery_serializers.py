from rest_framework import serializers
from Lottery.models.lottery_models import LotteryRewards, Lottery
from Users.serializers.users_serializers import OtherUserProfileSerializer


class LotteryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lottery
        fields = ("id", "name", "lottery_datetime")


class LotteryRewardSerializer(serializers.ModelSerializer):
    user = OtherUserProfileSerializer(read_only=True)

    class Meta:
        model = LotteryRewards
        fields = ("place", "amount", "user")


class ActiveLotterySerializer(serializers.ModelSerializer):
    rewards = LotteryRewardSerializer(source="lotteryrewards_set", many=True, read_only=True)

    class Meta:
        model = Lottery
        fields = ['name', 'description', 'lottery_datetime', 'rewards']


class LotteryWinnersSerializer(serializers.ModelSerializer):
    winners = LotteryRewardSerializer(source="lotteryrewards_set", many=True, read_only=True)

    class Meta:
        model = Lottery
        fields = ("name", "lottery_datetime", "winners")


class LastLotteryUserStatusSerializer(serializers.Serializer):
    lottery = LotteryMiniSerializer()
    status = serializers.CharField()
    reward = LotteryRewardSerializer(allow_null=True)