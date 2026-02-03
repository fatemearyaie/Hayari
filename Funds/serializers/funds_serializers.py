from django.db import transaction
from rest_framework import serializers
from Funds.models import Donor
from Funds.models.funds_models import FundRaising, FundImage
from Users.models import CustomUser, Transaction, XPTracker
from Users.serializers.users_serializers import CitySerializer, UserProfileSerializer, OtherUserProfileSerializer


class FundImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundImage
        fields = ['image','id']

class FundRaisingSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    images = FundImagesSerializer(source='fundimage_set',many=True)
    class Meta:
        model = FundRaising
        fields =['id','title','current_donation','city','each_don_xp','images',
                 'start_date','end_date','description','is_available',
                 'latitude','longitude','website','total_amount', 'created_at']
class FundRaisingDetailSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    images = FundImagesSerializer(source='fundimage_set', many=True)
    class Meta:
        model = FundRaising
        fields = ['title','current_donation','city','each_don_xp','images','description','total_amount','start_date','end_date','latitude','longitude','website']
from rest_framework import serializers
from django.db import transaction
from Funds.models.funds_models import Donor
from Users.models import CustomUser


class DonateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donor
        fields = ['amount']



class DonorSerializer(serializers.ModelSerializer):
    user = OtherUserProfileSerializer()
    class Meta:
        model = Donor
        fields = ['user','amount','place','datetime','xp']

class MyDonoationSerializer(serializers.ModelSerializer):
    fundraising = FundRaisingSerializer()
    user = UserProfileSerializer()
    class Meta:
        model = Donor
        fields = ['fundraising','user','amount','place','datetime','xp']


class MyDonationAnalyticsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    total_amount = serializers.IntegerField()