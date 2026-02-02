from django.db import models, transaction, connection
from Users.models import CustomUser
from Users.models.users_models import City


# Create your models here.
class FundRaising(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    title = models.CharField(max_length=70, null=False, blank=False)
    description = models.TextField(null=False, blank=False)
    total_amount = models.DecimalField(max_digits=12,decimal_places=0, null=False, blank=False)
    current_donation = models.DecimalField(max_digits=12, decimal_places=0, editable=False, default=0)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    each_don_xp = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Fund Raising'
        verbose_name_plural = 'Fund Raisings'

        indexes = [
            models.Index(fields=['title'], name='fund_title_idx'),
            models.Index(fields=['total_amount'], name='fund_amount_idx'),
            models.Index(fields=['current_donation'], name='fund_donation_idx'),
            models.Index(fields=['start_date'], name='fund_start_idx'),
            models.Index(fields=['end_date'], name='fund_end_idx'),
            models.Index(fields=['is_available'], name='fund_available_idx'),
            models.Index(fields=['latitude'], name='fund_latitude_idx'),
            models.Index(fields=['longitude'], name='fund_longitude_idx'),
            models.Index(fields=['website'], name='fund_website_idx'),
            models.Index(fields=['each_don_xp'],name='fund_each_don_idx')
        ]

    def __str__(self):
        return self.title

class FundImage(models.Model):
    image = models.ImageField(upload_to='funds/')
    Fund = models.ForeignKey(FundRaising, models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Image'
        verbose_name_plural = 'Images'

    def __str__(self):
        return str(self.pk)

class Donor(models.Model):
    fundraising = models.ForeignKey(FundRaising, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12,decimal_places=0, null=False, blank=False)
    place = models.PositiveIntegerField(editable=False)
    datetime = models.DateTimeField(auto_now_add=True)
    xp = models.PositiveIntegerField(default=0)


    def save(self, *args, **kwargs):
        if not self.pk:
            with transaction.atomic():
                last_donor = Donor.objects.filter(fundraising=self.fundraising).order_by('-place').first()
                self.place = (last_donor.place + 1) if last_donor else 1
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Donor'
        verbose_name_plural = 'Donors'

        indexes = [
            models.Index(fields=['user'], name='donor_user_idx'),
            models.Index(fields=['amount'], name='donor_amount_idx'),
            models.Index(fields=['place'], name='donor_place_idx'),
            models.Index(fields=['datetime'], name='donor_datetime_idx'),
            models.Index(fields=['xp'], name='donor_xp_idx')
        ]


    def __str__(self):
        return str(self.amount)