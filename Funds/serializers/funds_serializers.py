from rest_framework import serializers

from Funds.models import Donor
from Funds.models.funds_models import FundRaising, FundImage
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

class DonorSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer()
    class Meta:
        model = Donor
        fields = ['user','amount','place','datetime','xp']

class MyDonorSerializer(serializers.ModelSerializer):
    fundraising = FundRaisingSerializer()
    user = UserProfileSerializer()
    class Meta:
        model = Donor
        fields = ['fundraising','user','amount','place','datetime','xp']