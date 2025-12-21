from datetime import timedelta
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone
from Users.utils.managers import CustomUserManager
from django.utils.translation import gettext_lazy as _



# Create your models here.
class CustomUser(AbstractBaseUser,PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=25, null=True, blank=True)
    phone = models.CharField(max_length=12, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    image = models.ImageField(upload_to='users/images/', null=True, blank=True)
    total_score = models.PositiveIntegerField(default=0)
    month_score = models.PositiveIntegerField(default=0)
    balance = models.DecimalField(max_digits=9, decimal_places=0, default=0)
    description = models.TextField(null=True, blank=True)

    date_joined = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    version = models.CharField(default='1.0.0', max_length=20)

    class Meta:
        verbose_name = 'CustomUser'
        verbose_name_plural = 'CustomUsers'

        indexes = [
            models.Index(fields=['username'], name='username_idx'),
            models.Index(fields=['phone'], name='phone_idx'),
            models.Index(fields=['email'], name='email_idx'),
            models.Index(fields=['total_score'], name='total_score_idx'),
            models.Index(fields=['month_score'], name='month_score_idx'),
            models.Index(fields=['balance'], name='balance_idx')
        ]

        constraints = [
            models.CheckConstraint(
                check=Q(phone__isnull=False)|Q(email__isnull=False),name='phone_or_email_required'
            )
        ]

    class ModerationStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        READ_ONLY = 'read_only', _('Read-only')  # can login + read, but CANNOT POST/PUT/PATCH/DELETE
        DISABLED = 'disabled', _('Disabled')  # optional: block login entirely (you can tie this to is_active=False)

    moderation_status = models.CharField(
        max_length=16,
        choices=ModerationStatus.choices,
        default=ModerationStatus.ACTIVE,
        db_index=True,
    )
    moderation_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    moderation_reason = models.CharField(max_length=255, blank=True)

    def is_read_only(self) -> bool:
        """True if user is currently in read-only window."""
        if self.moderation_status != self.ModerationStatus.READ_ONLY:
            return False
        return True

    def is_disabled(self) -> bool:
        if self.moderation_status == self.ModerationStatus.DISABLED:
            return True
        return False

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.username


def get_random_code():
    from random import randint
    return str(randint(100000, 999999))
class OTP(models.Model):
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    otp = models.CharField(max_length=6, default=get_random_code)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.created_at + timedelta(minutes=5) < timezone.now()
    def __str__(self):
        return self.otp
    class Meta:
        verbose_name = 'OTP'
        verbose_name_plural = 'OTPs'

        constraints = [
            models.CheckConstraint(
                check=Q(phone__isnull=False) | Q(email__isnull=False),
                name="otp_phone_or_email_required",
            )
        ]

        indexes =[
            models.Index(fields=['phone'], name='otp_phone_idx'),
            models.Index(fields=['email'], name='otp_email_idx')
        ]


class Country(models.Model):
    name = models.CharField(max_length=50, null=False)
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

        indexes = [
            models.Index(fields=['name'], name='country_name_idx')
        ]

    def __str__(self):
        return self.name

class City(models.Model):
    name = models.CharField(max_length=50, null=False)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    is_available = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'

        constraints = [
            models.UniqueConstraint(fields=["country", "name"], name="uniq_city_country_name")
        ]

        indexes = [
            models.Index(fields=['name'], name='city_name_idx'),
        ]
    def __str__(self):
        return self.name