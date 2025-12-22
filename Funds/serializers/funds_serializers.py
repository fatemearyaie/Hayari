from rest_framework import serializers
from Funds.models.funds_models import FundRaising, FundImage
from Users.serializers.users_serializers import CitySerializer




class FundImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundImage
        fields = ['image']

class FundRaisingSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    images = FundImagesSerializer(many=True ,source='fundimage_set',)
    class Meta:
        model = FundRaising
        fields =['title','total_amount','current_donation','city','website','each_don_xp','images']

