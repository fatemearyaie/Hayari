from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from Users.models.users_models import City

CACHE_KEY = "city:all"

@receiver(post_save, sender=City)
def clear_city_cache_on_save(sender, instance, **kwargs):
    cache.delete(CACHE_KEY)

@receiver(post_delete, sender=City)
def clear_city_cache_on_delete(sender, instance, **kwargs):
    cache.delete(CACHE_KEY)
