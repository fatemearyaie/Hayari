from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status, mixins
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from Funds.services.donation import donate_fundraising
from Funds.services.list_cache import cached_list
from Funds.models.funds_models import FundRaising, Donor
from Funds.serializers.funds_serializers import FundRaisingSerializer, FundRaisingDetailSerializer, DonateSerializer, \
    DonorSerializer, MyDonoationSerializer, MyDonationAnalyticsSerializer
from Users.models.users_models import CustomUser


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


def get_target_user(request, param_name="user_id"):
    user_id = request.query_params.get(param_name) or request.query_params.get("id")
    if not user_id:
        return request.user


    return get_object_or_404(CustomUser, pk=user_id)


def get_target_user_by_pk(request, pk):
    if pk is None:
        return request.user

    if str(pk) == str(request.user.pk):
        return request.user

    return get_object_or_404(CustomUser, pk=pk)


class DonateGV(mixins.ListModelMixin, viewsets.GenericViewSet):
    throttle_scope = "custom"
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["amount", "datetime"]
    ordering_fields = ["datetime", "amount"]
    ordering = ["-datetime"]

    serializer_class = MyDonoationSerializer

    def list(self, request, *args, **kwargs):
        target_user = request.user

        qs = (
            Donor.objects
            .filter(user=target_user)
            .select_related("fundraising")
            .order_by("-datetime")
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.serializer_class(page, many=True).data)

        return Response(self.serializer_class(qs, many=True).data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        target_user = get_target_user_by_pk(request, pk)

        qs = (
            Donor.objects
            .filter(user=target_user)
            .select_related("fundraising")
            .order_by("-datetime")
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.serializer_class(page, many=True).data)

        return Response(self.serializer_class(qs, many=True).data)


class MyDonationAnayticsView(viewsets.ViewSet):
    throttle_scope = "custom"
    permission_classes = [IsAuthenticated]

    def list(self, request):
        target_user = request.user

        agg = Donor.objects.filter(user=target_user).aggregate(
            count=Count("id"),
            total_amount=Sum("amount"),
        )

        payload = {
            "count": agg.get("count") or 0,
            "total_amount": agg.get("total_amount") or 0,
        }

        s = MyDonationAnalyticsSerializer(data=payload)
        s.is_valid(raise_exception=True)
        return Response(s.validated_data)

    def retrieve(self, request, pk=None):
        target_user = get_target_user_by_pk(request, pk)

        agg = Donor.objects.filter(user=target_user).aggregate(
            count=Count("id"),
            total_amount=Sum("amount"),
        )

        payload = {
            "count": agg.get("count") or 0,
            "total_amount": agg.get("total_amount") or 0,
        }

        s = MyDonationAnalyticsSerializer(data=payload)
        s.is_valid(raise_exception=True)
        return Response(s.validated_data)