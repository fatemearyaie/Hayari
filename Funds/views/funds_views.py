from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from Funds.models.funds_models import FundRaising
from Funds.serializers.funds_serializers import FundRaisingSerializer, FundRaisingDetailSerializer


# Create your views here.
class FundRaisingView(viewsets.ViewSet):
    filterset_fields = ['title', 'current_donation', 'city', 'each_don_xp', 'start_date']
    search_fields = ['title', 'start_date', 'city']
    ordering_fields = ['title', 'start_date']
    ordering = ['title', 'start_date']
    def list(self, request):
        queryset = FundRaising.objects.all().select_related('city').prefetch_related('fundimage_set')
        queryset = DjangoFilterBackend().filter_queryset(request, queryset, self)
        queryset = filters.SearchFilter().filter_queryset(request, queryset, self)
        queryset = filters.OrderingFilter().filter_queryset(request, queryset, self)

        serializer = FundRaisingSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = FundRaising.objects.all()
        fundraising = get_object_or_404(queryset, pk=pk)
        serializer = FundRaisingDetailSerializer(fundraising, context={'request': request})
        return Response(serializer.data)