from django.db import transaction
from django.db.models import F
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
        fields = ['name','id']

class CreateAdvertisementSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())
    category = serializers.PrimaryKeyRelatedField(queryset=AdCategory.objects.all())

    class Meta:
        model = Advertisement
        fields = ['city','category','title','image', 'video','website']

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({'اخطار': 'احراز هویت کنید.'})

        image = attrs.get('image')
        video = attrs.get('video')

        if not image and not video:
            raise serializers.ValidationError({'فایل': 'فایل تصویر یا ویدیو ارسال کنید.'})

        if image and video:
            raise serializers.ValidationError({'فایل': 'لطفا فقط تصویر یا فقط ویدیو ارسال کنید.'})

        return attrs

    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        validated_data['status'] = Advertisement.AdStatus.Pending
        return super().create(validated_data)

class UpdateAdvertisementSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    category = AdCategorySerializer()

    class Meta:
        model = Advertisement
        fields = ['city','category','title','image', 'video','website']


class MyAdvertisementSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    category = AdCategorySerializer()

    class Meta:
        model = Advertisement
        fields = ['id','city', 'category', 'title', 'image', 'video', 'website','status','total_view','total_click','created_at','updated_at',]

class AdvertisementReadSerializer(serializers.ModelSerializer):
    city = CitySerializer()
    category = AdCategorySerializer()

    class Meta:
        model = Advertisement
        fields = ['id','city', 'category', 'title', 'image', 'video', 'website']

class AdEventSerializer(serializers.ModelSerializer):
    ad = AdvertisementReadSerializer(read_only=True)

    class Meta:
        model = AdEvent
        fields = ['event_type', 'ad']

    def validate(self, attrs):
        request = self.context.get('request')
        ad = self.context.get('ad')

        if not request or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError({'اخطار': 'احراز هویت کنید'})

        if ad is None:
            raise serializers.ValidationError({'اخطار': 'هیچ تبلیغی وجود ندارد'})

        attrs['user'] = request.user
        attrs['ad'] = ad
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        ad = validated_data['ad']
        event_type = validated_data['event_type']

        with transaction.atomic():
            event, created = AdEvent.objects.get_or_create(
                user=user,
                ad=ad,
                defaults={'event_type': event_type}
            )

            if not created:
                raise serializers.ValidationError({
                    'اخطار': 'این تبلیغ قبلا توسط شما دیده شده است.'
                })

            if event_type == 'view':
                Advertisement.objects.filter(pk=ad.pk).update(
                    total_view=F('total_view') + 1
                )
            elif event_type == 'click':
                Advertisement.objects.filter(pk=ad.pk).update(
                    total_click=F('total_click') + 1
                )
            else:
                raise serializers.ValidationError({
                    'event_type': 'Invalid event type.'
                })

        return event
