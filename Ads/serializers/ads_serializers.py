from rest_framework import serializers
from Ads.models.ads_models import AdSetting, Advertisement, AdCategory




class AdSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdSetting
        fields = ['video_price','video_xp','banner_price','banner_xp','is_available']

class AdCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCategory
        fields = ['name']