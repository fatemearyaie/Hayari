from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from Users.models.users_models import CustomUser


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from Users.models.users_models import CustomUser


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from Users.models.users_models import CustomUser


@receiver(post_save, sender=CustomUser)
def cache_user(sender, instance, created, **kwargs):
    key = f"user:obj:{instance.id}"
    if created:
        cache.set(key, instance)
    else:
        cache.delete(key)


@receiver(post_delete, sender=CustomUser)
def clear_user_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f"user:obj:{instance.id}")
