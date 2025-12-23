from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action

from Funds.models.funds_models import FundRaising, Donor
from Funds.serializers.funds_serializers import FundRaisingSerializer, FundRaisingDetailSerializer, DonateSerializer, \
    DonorSerializer
from Users.models.users_models import XPTracker, CustomUser
from Users.models.transactions_models import Transaction

# Create your views here.
class FundRaisingView(viewsets.ViewSet):

    def list(self, request):
        self.filterset_fields = ['title', 'current_donation', 'city', 'each_don_xp', 'start_date']
        self.search_fields = ['title', 'start_date', 'city']
        self.ordering_fields = ['title', 'start_date']

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


    @action(detail=True, methods=['get'])
    def donors(self, request, pk=None):
        fundraising = get_object_or_404(FundRaising, pk=pk)
        queryset = Donor.objects.filter(fundraising=fundraising).select_related('user').order_by('-datetime')

        self.filterset_fields = ['amount', 'place', 'xp', 'datetime']
        self.search_fields = ['user__username', 'user__phone']
        self.ordering_fields = ['amount', 'datetime']

        queryset = DjangoFilterBackend().filter_queryset(request, queryset, self)
        queryset = filters.SearchFilter().filter_queryset(request, queryset, self)
        queryset = filters.OrderingFilter().filter_queryset(request, queryset, self)

        serializer = DonorSerializer(queryset, many=True)
        return Response(serializer.data)


class DonateView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    @action(detail=True, methods=['post'])
    def donate(self, request, pk=None):
        serializer = DonateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        fundraising = get_object_or_404(FundRaising, pk=pk)
        amount = serializer.validated_data['amount']

        if not fundraising.is_available:
            return Response({'this fundraising is not available anymore'})

        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)

            if user.balance <= amount:
                return Response({'Balance':"Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

            Donor.objects.create(
                user=user,
                amount=amount,
                xp=fundraising.each_don_xp,
                fundraising=fundraising
            )

            Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TransactionType.Withdraw,
                transaction_status=Transaction.TransactionStatus.COMPLETE,
                payment_gateway=Transaction.PaymentGateWay.app,
                amount=amount,
            )


            XPTracker.objects.create(
                user=user,
                xp=fundraising.each_don_xp,
                reason = XPTracker.Reason.donation,
            )
        return Response({'status': 'Donation successful'}, status=status.HTTP_200_OK)

