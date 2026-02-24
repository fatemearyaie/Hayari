from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from Users.models.users_models import CustomUser, OTP, City
from rest_framework_simplejwt.tokens import RefreshToken
from Users.utils.identifier import username_identifier


class OTPGeneratorSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    def validate(self, attrs):
        username = attrs['username'].strip()

        if not username:
            raise serializers.ValidationError({"اخطار":"شماره تلفن یا ایمیل خود را وارد کنید"})

        identifiers = username_identifier(username)

        attrs["email"] = identifiers["email"]
        attrs["phone"] = identifiers["phone"]

        return attrs


    def create(self, validated_data):
        phone = validated_data['phone']
        email = validated_data['email']

        otp_obj = OTP.objects.create(phone=phone, email=email)
        return otp_obj


class OTPVerifySerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    otp = serializers.CharField(max_length=6)
    def validate(self, attrs):
        username = attrs['username'].strip()
        otp = attrs['otp'].strip()

        if not otp:
            raise serializers.ValidationError({"اخطار":"لطفا کدی که به شماره تلفن یا ایمیل شده ارسال شده است را وارد کنید"})

        ident = username_identifier(username)

        qs = OTP.objects.filter(
            email=ident["email"],
            phone=ident["phone"],
            is_used=False,
        ).order_by("-created_at")

        otp_instance = qs.first()



        if not otp_instance.otp:
            raise serializers.ValidationError({"اخطار":"کد پیدا نشد."})
        if otp_instance.otp != otp:
            raise serializers.ValidationError({"اخطار":"کد نامعبتر است"})
        if otp_instance.is_used:
            raise serializers.ValidationError({"اخطار":"این کد قبلا استفاده شده است."})
        if otp_instance.is_expired():
            raise serializers.ValidationError({"اخطار":"این کد منقضی شده است دوباره تلاش کنید."})
        attrs['email'] = otp_instance.email
        attrs['phone'] = otp_instance.phone
        attrs['otp_instance'] = otp_instance
        return attrs

    def save(self, **kwargs):
        otp_instance = self.validated_data['otp_instance']
        email = self.validated_data['email']
        phone = self.validated_data['phone']

        with transaction.atomic():
            otp_instance.is_used = True
            otp_instance.save()

            if email:
                user= CustomUser.objects.filter(username=email).first()
                created = False
                if not user:
                    user = CustomUser.objects.create_user(email=email)
                    created = True
            elif phone:
                user = CustomUser.objects.filter(username=phone).first()
                created = False
                if not user:
                    user = CustomUser.objects.create_user(phone=phone)
                    created = True

            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            return {
                "username":user.username,
                'access_token': str(access),
                'refresh_token': str(refresh),
                'created': created,
            }



class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'name', 'phone', 'email', 'image','description', 'balance','total_score','month_score']
        read_only_fields = ['balance','total_score', 'month_score']
class OtherUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['name','image','description']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['name','id']



class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=False, allow_blank=False)
    code = serializers.CharField(required=False)
    code_verifier = serializers.CharField(required=False)
    redirect_uri = serializers.URLField(required=False)

    def validate(self, attrs):
        if not attrs.get("id_token") and not (attrs.get("code") and attrs.get("code_verifier") and attrs.get("redirect_uri")):
            raise serializers.ValidationError("Provide either id_token or (code, code_verifier, redirect_uri).")
        return attrs



class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["email"]

    def create(self, validated_data):
        email = (validated_data.get("email") or "").strip().lower()
        if not email:
            raise serializers.ValidationError({"email": "email is required"})

        user = CustomUser(username=email, email=email, is_active=True)
        user.set_unusable_password()
        user.save()
        return user