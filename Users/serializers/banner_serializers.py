from rest_framework import serializers
from Users.models.banner_models import HomeBanner




class HomeBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeBanner
        fields = ['banner','message', 'url']