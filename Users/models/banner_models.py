from django.db import models
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

