from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from Users.tasks import send_otp_sms, send_otp_email
from Users.serializers.users_serializers import OTPGeneratorSerializer, OTPVerifySerializer, UserProfileSerializer
from Users.utils.identifier import username_identifier
from rest_framework.views import APIView

class OTPGeneratorView(APIView):
    throttle_scope = 'custom'
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
        serializer = OTPVerifySerializer(data=request.user)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)

class UserProfileView(APIView):
    throttle_scope = 'user'
    permission_classes = [IsAuthenticated]
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)