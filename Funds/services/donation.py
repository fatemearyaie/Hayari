from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from types import SimpleNamespace

from Funds.models.funds_models import FundRaising, Donor
from Funds.serializers.funds_serializers import DonateSerializer
from Notification.services.send_notification import send_notification
from Funds.services.list_cache import bump_version

@transaction.atomic
def donate_fundraising(*, user, fundraising_id, amount):
    amount = Decimal(amount)

    fundraising = get_object_or_404(
        FundRaising.objects.select_for_update(),
        pk=fundraising_id
    )

    donor = Donor.objects.create(
        user=user,
        fundraising=fundraising,
        amount=amount,
        xp=fundraising.each_don_xp,
    )

    FundRaising.objects.filter(pk=fundraising_id).update(
        current_donation=F("current_donation") + amount
    )

    bump_version(f"fundraising:{fundraising_id}:donors:ver")
    send_notification(user=user, message_type="donation_success")

    return donor
