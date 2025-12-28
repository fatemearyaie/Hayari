from rest_framework import serializers
from Ads.models.ads_models import AdSetting, Advertisement, AdCategory, AdEvent
from Users.models import City
from Users.serializers.users_serializers import CitySerializer


class AdSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdSetting
        fields = ['video_price','video_xp','banner_price','banner_xp','is_available']

class AdCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCategory
        fields = ['name']

class CreateAdvertisementSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    category = serializers.PrimaryKeyRelatedField(queryset=AdCategory.objects.all())

    class Meta:
        model = Advertisement
        fields = ['city','category','title','image', 'video','website']

    def validate(self, attrs):
        user = self.context.get('request').user
        image = attrs.get('image')
        video = attrs.get('video')

        title = (attrs.get('title') or '').strip()

        if not image and not video:
            raise serializers.ValidationError({'files':'Send either image or video.'})

        if Advertisement.objects.filter(
                user=user,title=title,).exists():
            raise serializers.ValidationError(
                {'duplicate': 'You already created an ad with the same city/category/title.'})

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')

        validated_data['user'] = request.user
        validated_data['status'] = Advertisement.AdStatus.Pending

        return super().create(validated_data)

class UpdateAdvertisementSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    category = AdCategorySerializer()

    class Meta:
        model = Advertisement
        fields = ['city','category','title','image', 'video','website']

    def validate(self, attrs):
        user = self.context.get('request').user

        title = (attrs.get('title') or '').strip()
        city = attrs.get('city')
        category = attrs.get('category')

        if Advertisement.objects.filter(
                user=user,city=city,category=category,title=title,).exists():
            raise serializers.ValidationError(
                {'duplicate': 'You already created an ad with the same city/category/title.'})

        return attrs

class MyAdvertisementSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    category = AdCategorySerializer()

    class Meta:
        model = Advertisement
        fields = ['city', 'category', 'title', 'image', 'video', 'website','status','total_view','total_click','created_at','updated_at',]
class AdvertisementReadSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    category = AdCategorySerializer()

    class Meta:
        model = Advertisement
        fields = ['city', 'category', 'title', 'image', 'video', 'website']


class AdEventSerializer(serializers.ModelSerializer):
    ad = AdvertisementReadSerializer(read_only=True)
    class Meta:
        model = AdEvent
        fields = ['event_type','ad']

    def validate(self, attrs):
        request = self.context.get('request')
        ad = self.context.get('ad')

        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')

        if ad is None:
            raise serializers.ValidationError('Ad is required in serializer context.')

        attrs['user'] = request.user
        attrs['ad'] = ad
        return attrs

    def create(self, validated_data):
        event, created = AdEvent.objects.get_or_create(
            user=validated_data['user'],
            ad=validated_data['ad'],
            defaults={'event_type': validated_data['event_type']}
        )
        if not created:
            raise serializers.ValidationError("you can not change your action to this ad, or set action twice!")
        return event