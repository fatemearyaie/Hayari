from django.db import transaction
from rest_framework import serializers

from Funds.models import Donor
from Funds.models.funds_models import FundRaising, FundImage
from Users.models import CustomUser, Transaction, XPTracker
from Users.serializers.users_serializers import CitySerializer, UserProfileSerializer


class FundImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundImage
        fields = ['image']

class FundRaisingSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    images = FundImagesSerializer(source='fundimage_set',many=True)
    class Meta:
        model = FundRaising
        fields =['title','current_donation','city','each_don_xp','images', 'start_date']
class FundRaisingDetailSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    images = FundImagesSerializer(source='fundimage_set', many=True)
    class Meta:
        model = FundRaising
        fields = ['title','current_donation','city','each_don_xp','images','description','total_amount','start_date','end_date','latitude','longitude','website']


class DonateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donor
        fields = ['amount']

    def validate(self, attrs):
        amount = attrs['amount']
        user = self.context['request'].user
        fundraising = self.context["fundraising"]

        if not fundraising.is_available:
            return serializers.ValidationError({"detail": "this fundraising is not available anymore"})
        if user.balance <= amount:
            return serializers.ValidationError({"detail": "Insufficient balance"})

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        fundraising = self.context["fundraising"]
        amount = validated_data["amount"]

        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=user.pk)

            donor = Donor.objects.create(
                user=user,
                amount=amount,
                xp=fundraising.each_don_xp,
                fundraising=fundraising,)

        return donor

class DonorSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer()
    class Meta:
        model = Donor
        fields = ['user','amount','place','datetime','xp']

class MyDonoationSerializer(serializers.ModelSerializer):
    fundraising = FundRaisingSerializer()
    user = UserProfileSerializer()
    class Meta:
        model = Donor
        fields = ['fundraising','user','amount','place','datetime','xp']