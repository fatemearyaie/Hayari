from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F

from Ads.models.ads_models import Advertisement, AdSetting
from Users.models.transactions_models import Transaction
from Ads.services.video_duration import (
    get_video_duration_seconds_from_path,
    get_duration_bucket,
    VideoDurationError,
)


@receiver(pre_save, sender=Advertisement)
def refund_on_ad_rejected(sender, instance: Advertisement, **kwargs):

    if not instance.pk:
        return

    try:
        old = Advertisement.objects.get(pk=instance.pk)
    except Advertisement.DoesNotExist:
        return

    if old.status == instance.status:
        return

    if old.status == Advertisement.AdStatus.Rejected:
        return
    if instance.status != Advertisement.AdStatus.Rejected:
        return

    settings = AdSetting.objects.order_by("-id").first()
    if not settings:
        return

    refund_key = f"refund_ad:{instance.pk}"
    if Transaction.objects.filter(user=instance.user, description=refund_key).exists():
        return

    refund_amount = None

    # --- IMAGE ---
    if instance.image:
        refund_amount = settings.banner_price

    # --- VIDEO ---
    elif instance.video:
        try:
            video_path = instance.video.path
            seconds = get_video_duration_seconds_from_path(video_path)
            bucket = get_duration_bucket(seconds)  # 30 / 60 / 90 / 120
        except (NotImplementedError, AttributeError, VideoDurationError):
            return

        video_price_map = {
            30: settings.video_price_30,
            60: settings.video_price_60,
            90: settings.video_price_90,
            120: settings.video_price_120,
        }

        refund_amount = video_price_map.get(bucket)

    if refund_amount is None or refund_amount <= 0:
        return

    with transaction.atomic():
        user = instance.user

        user.balance = F("balance") + refund_amount
        user.save(update_fields=["balance"])
        user.refresh_from_db()

        Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TransactionType.Deposit,
            transaction_status=Transaction.TransactionStatus.COMPLETE,
            payment_gateway=Transaction.PaymentGateWay.app,
            description=refund_key,
            amount=refund_amount,
            balance_after=user.balance,
        )