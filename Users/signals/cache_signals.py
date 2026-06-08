from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache

from Users.models.banner_models import Banner
from Users.models.users_models import City

CACHE_KEY = "city:all"

@receiver(pre_save, sender=City)
def city_presave_capture_old_is_available(sender, instance: City, **kwargs):
    if not instance.pk:
        instance._old_is_available = None
        return

    old_val = (
        sender.objects
        .filter(pk=instance.pk)
        .values_list("is_available", flat=True)
        .first()
    )
    instance._old_is_available = old_val

@receiver(post_save, sender=City)
def invalidate_available_cities_cache_on_change(sender, instance: City, created: bool, **kwargs):
    if created:
        if instance.is_available:
            cache.delete(CACHE_KEY)
        return
    old_val = getattr(instance, "_old_is_available", None)
    if old_val is None:
        cache.delete(CACHE_KEY)
        return

    if bool(old_val) != bool(instance.is_available):
        cache.delete(CACHE_KEY)

@receiver(post_delete, sender=City)
def invalidate_available_cities_cache_on_delete(sender, instance: City, **kwargs):
    cache.delete(CACHE_KEY)




BANNER_CACHE_KEY = "banner:active"
@receiver(pre_save, sender=Banner)
def banner_presave_capture_old_is_active(sender, instance: Banner, **kwargs):
    if not instance.pk:
        instance._old_is_active = None
        return

    old_val = (
        sender.objects
        .filter(pk=instance.pk)
        .values_list("is_active", flat=True)
        .first()
    )
    instance._old_is_active = old_val

@receiver(post_save, sender=Banner)
def invalidate_banner_cache_on_is_active_change(sender, instance: Banner, created: bool, **kwargs):
    if created:
        if instance.is_active:
            cache.delete(BANNER_CACHE_KEY)
        return

    old_is_active = getattr(instance, "_old_is_active", None)

    if old_is_active is None:
        cache.delete(BANNER_CACHE_KEY)
        return

    if bool(old_is_active) != bool(instance.is_active):
        cache.delete(BANNER_CACHE_KEY)

@receiver(post_delete, sender=Banner)
def invalidate_banner_cache_on_delete(sender, instance: Banner, **kwargs):
    cache.delete(BANNER_CACHE_KEY)