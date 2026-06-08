from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers
from Ads.models.ads_models import AdSetting, Advertisement, AdCategory, AdEvent
from Users.models import City, Transaction
from Users.serializers.users_serializers import CitySerializer
from Ads.services.video_duration import (
    get_video_duration_seconds,
    get_duration_bucket,
    VideoDurationError,
)

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
        fields = ['city', 'category', 'title', 'image', 'video', 'website']


    def validate(self, attrs):
        request = self.context.get('request')
        image = attrs.get('image')
        video = attrs.get('video')
        setting = AdSetting.objects.get(is_available=True)

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({'اخطار': 'احراز هویت کنید.'})

        if not image and not video:
            raise serializers.ValidationError({'فایل': 'فایل تصویر یا ویدیو ارسال کنید.'})

        if image and video:
            raise serializers.ValidationError({'فایل': 'لطفا فقط تصویر یا فقط ویدیو ارسال کنید.'})

        if image:
            image_price = setting.banner_price
            if request.user.balance < image_price:
                raise serializers.ValidationError({
                    'موجودی': 'موجودی شما برای تبلیغ تصویری کافی نیست.'
                })

            attrs["calculated_price"] = image_price
            attrs["ad_type"] = "image"

        if video:
            try:
                seconds = get_video_duration_seconds(video)
                bucket = get_duration_bucket(seconds)  # 30/60/90/120
            except VideoDurationError as e:
                raise serializers.ValidationError({"ویدیو": str(e)})

            settings = AdSetting.objects.get(is_available=True)
            if not settings:
                raise serializers.ValidationError({"تنظیمات": "تنظیمات تبلیغات تعریف نشده است."})

            price_map = {
                30: settings.video_price_30,
                60: settings.video_price_60,
                90: settings.video_price_90,
                120: settings.video_price_120,
            }

            video_price = price_map.get(bucket)

            if video_price is None:
                raise serializers.ValidationError({"ویدیو": "قیمت این نوع ویدیو تنظیم نشده است."})

            if request.user.balance < video_price:
                raise serializers.ValidationError({
                    "موجودی": f"موجودی برای تبلیغ ویدیویی {bucket} ثانیه کافی نیست."
                })

            attrs["calculated_price"] = video_price
            attrs["ad_type"] = "video"
            attrs["video_bucket"] = bucket
            attrs["video_seconds"] = seconds

        return attrs
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        price = validated_data.pop("calculated_price")
        validated_data.pop("ad_type")
        validated_data.pop("video_bucket", None)
        validated_data.pop("video_seconds", None)

        validated_data['user'] = user

        with transaction.atomic():
            if price:
                user.balance = F('balance') - price
                user.save(update_fields=['balance'])
                user.refresh_from_db()

                Transaction.objects.create(
                    user=user,
                    transaction_type=Transaction.TransactionType.Withdraw,
                    transaction_status=Transaction.TransactionStatus.COMPLETE,
                    payment_gateway=Transaction.PaymentGateWay.app,
                    description="هزینه ساخت تبلیغ",
                    amount=price,
                    balance_after=user.balance
                )

            ad = super().create(validated_data)

        return ad

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
        today = timezone.localdate()

        with transaction.atomic():
            Advertisement.objects.select_for_update().only("id").get(pk=ad.pk)

            already_today = AdEvent.objects.filter(
                user_id=user.id,
                ad_id=ad.id,
                event_date=today,
            ).exists()

            if already_today:
                raise serializers.ValidationError({'اخطار': 'شما امروز برای این تبلیغ قبلاً رویداد ثبت کرده‌اید.'})

            event = AdEvent.objects.create(
                user=user,
                ad=ad,
                event_type=event_type,
                event_date=today,
            )

            if event_type == AdEvent.EventType.View:
                Advertisement.objects.filter(pk=ad.pk).update(
                    total_view=F('total_view') + 1
                )
            elif event_type == AdEvent.EventType.Click:
                Advertisement.objects.filter(pk=ad.pk).update(
                    total_click=F('total_click') + 1
                )
            else:
                raise serializers.ValidationError({'event_type': 'Invalid event type.'})

        return event