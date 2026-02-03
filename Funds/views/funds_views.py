from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, filters, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action

from Funds.services.donation import donate_fundraising
from Funds.services.list_cache import cached_list, bump_version
from Notification.services.send_notification import send_notification
from Funds.models.funds_models import FundRaising, Donor
from Funds.serializers.funds_serializers import FundRaisingSerializer, FundRaisingDetailSerializer, DonateSerializer, \
    DonorSerializer, MyDonoationSerializer, MyDonationAnalyticsSerializer
from Users.models.users_models import XPTracker, CustomUser
from Users.models.transactions_models import Transaction

# Create your views here.
class FundRaisingGV(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    throttle_scope = "custom"

    queryset = FundRaising.objects.all().select_related('city').prefetch_related('fundimage_set')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ['title', 'current_donation', 'city', 'each_don_xp', 'start_date']
    search_fields = ['title']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['created_at', 'total_amount']

    def get_serializer_class(self):
        if self.action == "retrieve":
            return FundRaisingDetailSerializer
        return FundRaisingSerializer

class DonateGV(mixins.ListModelMixin, viewsets.GenericViewSet):
    throttle_scope = "custom"
    permission_classes = [IsAuthenticated]

    serializer_class = DonorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["amount", "datetime"]
    ordering_fields = ["datetime", "amount"]
    ordering = ["-datetime"]

    def list(self, request, *args, **kwargs):
        queryset = (
            Donor.objects
            .filter(user=request.user)
            .select_related("fundraising")
            .order_by("-datetime")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MyDonoationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MyDonoationSerializer(queryset, many=True)
        return Response(serializer.data)


    @action(detail=True, methods=["get"], url_path="donors")
    def donors(self, request, pk=None):
        def compute():
            qs = (
                Donor.objects
                .filter(fundraising_id=pk)
                .select_related("user")
                .order_by("-datetime")
            )

            qs = DjangoFilterBackend().filter_queryset(request, qs, self)
            qs = filters.SearchFilter().filter_queryset(request, qs, self)
            qs = filters.OrderingFilter().filter_queryset(request, qs, self)

            page = self.paginate_queryset(qs)
            if page is not None:
                data = DonorSerializer(page, many=True).data
                return self.get_paginated_response(data).data

            return DonorSerializer(qs, many=True).data

        data = cached_list(
            namespace=f"fundraising:{pk}:donors",
            version_key=f"fundraising:{pk}:donors:ver",
            query_params=request.query_params,
            compute=compute,
        )
        return Response(data)

    @action(detail=True, methods=["post"], url_path="donate")
    def donate(self, request, pk=None):
        user = request.user
        amount = request.data.get('amount')

        if not amount:
            return Response(
                {"detail": "مقدار اهدا را وارد کنید"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        donate_fundraising(
            user=user,
            fundraising_id=pk,
            amount=amount,
        )

        return Response(
            {"status": "اهدا با موفقیت انجام شد"},
            status=status.HTTP_200_OK,
        )

class MyDonationAnayticsView(viewsets.ViewSet):
    throttle_scope = 'custom'
    permission_classes = [IsAuthenticated]
    def list(self, request):
        qs = Donor.objects.filter(user=request.user).aggregate(
            count=Count('id'),
            total_amount=Sum('amount')
        )
        payload = {
            "count": qs.get("count") or 0,
            "total_amount": qs.get("total_amount") or 0,
        }

        serializer = MyDonationAnalyticsSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)