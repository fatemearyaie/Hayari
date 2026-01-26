from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from types import SimpleNamespace

from Funds.models.funds_models import FundRaising
from Funds.serializers.funds_serializers import DonateSerializer
from Notification.services.send_notification import send_notification
from Funds.services.list_cache import bump_version


@transaction.atomic
def donate_fundraising(*, user, fundraising_id, amount, charge_wallet=True, request=None):
    fundraising = get_object_or_404(FundRaising, pk=fundraising_id)

    amount = Decimal(amount)

    if request is None:
        request = SimpleNamespace(user=user, data={"amount": amount})

    serializer = DonateSerializer(
        data={"amount": amount},
        context={
            "request": request,
            "fundraising": fundraising,
            "charge_wallet": charge_wallet,
        },
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    FundRaising.objects.filter(pk=fundraising_id).update(
        current_donation=F("current_donation") + amount
    )

    bump_version(f"fundraising:{fundraising_id}:donors:ver")
    send_notification(user=user, message_type="donation_success")
