from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from Users.models.users_models import CustomUser
from Users.models.users_models import XPTracker


@receiver(post_save, sender=XPTracker)
def apply_xp_and_fill_after_fields(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        user = CustomUser.objects.select_for_update().get(pk=instance.user_id)

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_xp = (
            XPTracker.objects
            .filter(user_id=user.pk, datetime_created__gte=month_start)
            .aggregate(total=Sum("xp"))["total"]
            or 0
        )
        CustomUser.objects.filter(pk=user.pk).update(
            total_score=F("total_score") + (instance.xp or 0),
            month_score=monthly_xp
        )

        user.refresh_from_db(fields=["total_score", "month_score"])

        XPTracker.objects.filter(pk=instance.pk).update(
            total_xp_after=user.total_score,
            month_xp_after=user.month_score,
        )
