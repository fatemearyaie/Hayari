from rest_framework import serializers
from Funds.models.funds_models import FundRaising, FundImage
from Users.serializers.users_serializers import CitySerializer




class FundImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundImage
        fields = ['image']

class FundRaisingSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    images = FundImagesSerializer(source='fundimage_set',many=True)
    class Meta:
        model = FundRaising
        fields =['title','current_donation','city','each_don_xp','images']
class FundRaisingDetailSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    images = FundImagesSerializer(source='fundimage_set', many=True)
    class Meta:
        model = FundRaising
        fields = ['title','current_donation','city','each_don_xp','images','description','total_amount','start_date','end_date','latitude','longitude','website']
