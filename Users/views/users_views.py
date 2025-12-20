from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Users.serializers.users_serializers import OTPGeneratorSerializer, OTPVerifySerializer


# Create your views here.
class OTPGeneratorView(APIView):
    def post(self, request):
        serializer = OTPGeneratorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'OTP':'OTP generated'}, status=status.HTTP_200_OK)

class OTPVerifyView(APIView):
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result)