from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response

from Funds.models.funds_models import FundRaising
from Funds.serializers.funds_serializers import FundRaisingSerializer, FundRaisingDetailSerializer


# Create your views here.
class FundRaisingView(viewsets.ViewSet):
    def list(self, request):
        queryset = FundRaising.objects.all().select_related('city').prefetch_related('fundimage_set')
        serializer = FundRaisingSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = FundRaising.objects.all()
        fundraising = get_object_or_404(queryset, pk=pk)
        serializer = FundRaisingDetailSerializer(fundraising, context={'request': request})
        return Response(serializer.data)