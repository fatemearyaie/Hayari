from django.db import models
from django.utils import timezone

from Users.models import CustomUser, City


# Create your models here.
class AdSetting(models.Model):
    video_price_30 = models.DecimalField(max_digits=18,decimal_places=0, default=0)
    video_price_60 = models.DecimalField(max_digits=18,decimal_places=0, default=0)
    video_price_90 = models.DecimalField(max_digits=18, decimal_places=0, default=0)
    video_price_120 = models.DecimalField(max_digits=18, decimal_places=0, default=0)
    video_xp = models.PositiveIntegerField(null=False, blank=False)
    banner_price = models.DecimalField(max_digits=18,decimal_places=0)
    banner_xp = models.PositiveIntegerField(null=False, blank=False)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AdSetting'
        verbose_name_plural = 'AdSettings'

        indexes = [
            models.Index(fields=['video_xp'], name='setting_video_xp_idx'),
            models.Index(fields=['banner_xp'], name='setting_banner_xp_idx'),
        ]

    def save(self, *args, **kwargs):
        if self.is_available:
            AdSetting.objects.filter(is_available=True).update(is_available=False)
        super().save(*args, **kwargs)



class AdCategory(models.Model):
    name = models.CharField(max_length=25)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AdCategory'
        verbose_name_plural = 'AdCategories'

        indexes = [
            models.Index(fields=['name'], name='ad_category_idx'),
        ]
    def __str__(self):
        return self.name


class Advertisement(models.Model):
    class AdStatus(models.TextChoices):
        Pending = 'pending','pending'
        Enable = 'enable','enable'
        Disable = 'disable','disable'
        Rejected = 'rejected','rejected'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    category = models.ForeignKey(AdCategory, on_delete=models.CASCADE)
    status = models.CharField(choices=AdStatus.choices,default=AdStatus.Pending)
    title = models.CharField(max_length=50, null=False, blank=False)
    image = models.ImageField(upload_to='ads/images/', null=True, blank=True)
    video = models.FileField(upload_to='ads/video/', null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    total_view = models.PositiveIntegerField(default=0)
    total_click = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)




    class Meta:
        verbose_name = 'Advertisement'
        verbose_name_plural = 'Advertisements'

        indexes =[
            models.Index(fields=['total_view'], name='Ad_total_view_idx'),
            models.Index(fields=['total_click'], name='Ad_total_click_idx')
        ]
    def __str__(self):
        return self.title



class AdEvent(models.Model):
    class EventType(models.TextChoices):
        Click = 'click', 'click'
        View = 'view','view'
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE)
    event_type = models.CharField(choices=EventType.choices, default=EventType.View)
    event_date = models.DateField(db_index=True, editable=False, null=True, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AdEvent'
        verbose_name_plural = 'AdEvents'

        indexes = [
            models.Index(fields=['event_type'], name='event_type_idx'),
        ]

    def __str__(self):
        return str(self.pk)

