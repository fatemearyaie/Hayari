from django.contrib import admin

from Users.models import XPTracker
from Users.models.banner_models import Banner,Version, LoginEntry, HomeBanner
from Users.models.transactions_models import Transaction
from Users.models.users_models import CustomUser, City, Country, OTP
from unfold.admin import ModelAdmin

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    list_display = ['username', 'name','total_score','month_score', 'balance']
    search_fields = ['username', 'name', 'email', 'phone']
    list_filter = ['total_score', 'version', 'date_joined']

@admin.register(OTP)
class OTPAdmin(ModelAdmin):
    list_display = ['phone','email','otp', 'is_used']
    search_fields = ['phone','email']
    list_filter = ['is_used']
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_available']
    search_fields = ['name']
    list_filter = ['is_available']


class CityInline(admin.TabularInline):
    model = City
    extra = 5

@admin.register(Country)
class CountryAdmin(ModelAdmin):
    list_display = ['name', 'is_available']
    search_fields = ['name', 'is_available']
    list_filter = ['is_available']
    inlines = [CityInline]


@admin.register(Transaction)
class transactionAdmin(ModelAdmin):
    list_display = ['user', 'transaction_type','transaction_status','payment_gateway','amount','balance_after','tracking_code']
    search_fields = ['tracking_code','transaction_status', 'transaction_type']
    list_filter = ['transaction_type','transaction_status','payment_gateway']

@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ['title','url','is_active']
    list_filter = ['is_active']
    search_fields = ['title']

@admin.register(XPTracker)
class XPTrackerAdmin(ModelAdmin):
    list_display = ['user', 'xp','reason','month_xp_after','datetime_created']
    list_filter = ['reason']
    search_fields = ['reason', 'datetime_created']



@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = (
        'version_number',
        'title',
        'is_force',
        'force_min_version',
    )
    list_filter = ('is_force',)
    search_fields = ('title', 'description')
    ordering = ('-version_number',)
    list_editable = ('is_force', 'force_min_version')
    fieldsets = (
        ('Version Info', {
            'fields': ('version_number', 'title', 'description')
        }),
        ('Force Update Settings', {
            'fields': ('is_force', 'force_min_version'),
        }),
    )


@admin.register(LoginEntry)
class LoginEntryAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'created_at',
    )
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'user__phone')
    ordering = ('-created_at',)


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_message')
    search_fields = ('message',)

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message

    short_message.short_description = 'Message Preview'
