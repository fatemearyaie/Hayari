from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from Ads.models.ads_models import AdEvent, AdSetting, Advertisement
from Users.models.users_models import XPTracker


@receiver(post_save, sender=AdEvent)
def create_xptracker_on_ad_event(sender, instance: AdEvent, created: bool, **kwargs):
    if not created:
        return

    with transaction.atomic():
        already_rewarded = AdEvent.objects.filter(
            user_id=instance.user_id,
            ad_id=instance.ad_id,
        ).exclude(pk=instance.pk).exists()

        if already_rewarded:
            return

        setting = (AdSetting.objects
                   .filter(is_available=True)
                   .order_by('-updated_at', '-id')
                   .only('video_xp', 'banner_xp')
                   .first())
        if not setting:
            return

        ad = Advertisement.objects.only('id', 'video').get(pk=instance.ad_id)
        is_video_ad = bool(ad.video)

        xp_value = setting.video_xp if is_video_ad else setting.banner_xp
        if not xp_value or xp_value <= 0:
            return

        XPTracker.objects.create(
            user_id=instance.user_id,
            xp=xp_value,
            reason=XPTracker.Reason.Ads,
        )