from django.db import transaction
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from Users.models import CustomUser
from Users.services.city_cache import get_cached_cities
from Users.tasks import send_otp_sms, send_otp_email
from Users.serializers.users_serializers import OTPGeneratorSerializer, OTPVerifySerializer, UserProfileSerializer, \
    CitySerializer, GoogleAuthSerializer, RegisterSerializer
from Users.utils.google_auth import GoogleOIDC
from Users.utils.identifier import username_identifier
from rest_framework.views import APIView

class OTPGeneratorView(APIView):
    throttle_scope = 'user'
    def post(self, request):
        serializer = OTPGeneratorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.save()

        identifier = username_identifier(request.data.get("username"))

        if identifier["phone"]:
            send_otp_sms.delay(identifier["phone"], otp.otp)

        elif identifier["email"]:
            send_otp_email.delay(identifier["email"], otp.otp)

        return Response(
            {"detail": "OTP generated"},
            status=status.HTTP_200_OK
        )


class OTPVerifyView(APIView):
    throttle_scope = 'custom'
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)

class UserProfileView(APIView):
    throttle_scope = 'user'
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = CustomUser.objects.get(id=request.user.id)
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = CustomUser.objects.get(id=request.user.id)
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

class CityView(APIView):
    throttle_scope = 'custom'
    def get(self, request):
        cities = get_cached_cities()
        return Response(cities)

class GoogleAuthView(APIView):
    authentication_classes = []  # public
    permission_classes = []

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 1) Get claims (either direct id_token or via code exchange)
        if "id_token" in data:
            claims = GoogleOIDC.verify_id_token(data["id_token"])
        else:
            tokens = GoogleOIDC.exchange_code_for_tokens(
                code=data["code"],
                code_verifier=data["code_verifier"],
                redirect_uri=data["redirect_uri"],
            )
            claims = GoogleOIDC.verify_id_token(tokens["id_token"])

        sub = claims["sub"]
        email = claims.get("email") or ""
        given_name = claims.get("given_name") or ""
        family_name = claims.get("family_name") or ""
        picture = claims.get("picture")  # optional

        with transaction.atomic():
            # Find existing social account
            try:
                user = CustomUser.objects.get(email=email)
                is_new = False
            except CustomUser.DoesNotExist:
                serializer = RegisterSerializer(data={'email': email})
                serializer.is_valid(raise_exception=True)
                user = serializer.save()
                is_new = True

            user.is_active = True
            user.save()
            refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                'is_new': is_new
            },
            status=status.HTTP_200_OK,
        )
