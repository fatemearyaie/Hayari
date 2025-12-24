from rest_framework import serializers
from Ads.models.ads_models import AdSetting, Advertisement




class AdSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdSetting
        fields = ['video_price','video_xp','banner_price','banner_xp','is_available']
