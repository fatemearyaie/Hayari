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
def donate_fundraising(*, user, fundraising_id, amount):

    amount = Decimal(amount)

    FundRaising.objects.filter(pk=fundraising_id).update(
        current_donation=F("current_donation") + amount
    )

    bump_version(f"fundraising:{fundraising_id}:donors:ver")
    send_notification(user=user, message_type="donation_success")
