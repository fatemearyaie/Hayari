from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from Funds.models import Donor
from Funds.models.funds_models import FundRaising
from Funds.services.list_cache import bump_version



@receiver(post_save, sender=Donor)
@receiver(post_delete, sender=Donor)
def donor_changed(sender, instance, **kwargs):
    bump_version(f"fundraising:{instance.fundraising_id}:donors:ver")