from django.db import models
from django.utils import timezone

from Users.models import CustomUser


class Banner(models.Model):
    title = models.CharField(max_length=50, null=False, blank=False)
    image = models.ImageField(upload_to='banners/', null=False, blank=False)
    url = models.URLField(max_length=200)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'

        indexes = [
            models.Index(fields=['title'], name='banner_title_idx'),
            models.Index(fields=['url'], name='banner_url_idx'),
            models.Index(fields=['is_active'], name='banner_active_idx'),
            models.Index(fields=['created_at'], name='banner_created_idx'),
        ]
    def __str__(self):
        return self.title

class Version(models.Model):
    version_number = models.IntegerField(default=1)
    title = models.CharField(max_length=1000, null=True, blank=True)
    description = models.TextField(max_length=1000, null=True, blank=True)
    is_force = models.BooleanField(default=False)
    force_min_version = models.IntegerField(default=1)

    class Meta:
        verbose_name = 'Version'
        verbose_name_plural = 'Versions'



class LoginEntry(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'LoginEntry'
        verbose_name_plural = 'LoginEntries'


class HomeBanner(models.Model):
    banner = models.ImageField(upload_to='banners/home')
    message = models.TextField(null=False, blank=False)
    url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = 'HomeBanner'
        verbose_name_plural = 'HomeBanners'
