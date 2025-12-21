from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from Users.tasks import send_otp_sms, send_otp_email
from Users.serializers.users_serializers import OTPGeneratorSerializer, OTPVerifySerializer
from Users.utils.identifier import username_identifier


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
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)