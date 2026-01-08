from django.shortcuts import get_object_or_404

from Funds.models.funds_models import FundRaising
from Funds.serializers.funds_serializers import DonateSerializer
from Notification.services.send_notification import send_notification
from Funds.services.list_cache import bump_version



def donate_fundraising(*, request, fundraising_id):
    fundraising = get_object_or_404(FundRaising, pk=fundraising_id)

    serializer = DonateSerializer(
        data=request.data,
        context={
            "request": request,
            "fundraising": fundraising,
        },
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    bump_version(f"fundraising:{fundraising_id}:donors:ver")

    send_notification(user=request.user,message_type="donation_success",)

    return {
        "message": "Donation successful",
        "fundraising": fundraising,
    }
