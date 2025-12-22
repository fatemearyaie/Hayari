from rest_framework import serializers
from Users.models.banner_models import Banner


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['title','image','url','is_active']