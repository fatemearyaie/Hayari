from django.contrib import admin
from django.contrib.humanize.templatetags.humanize import intcomma
from Users.models import XPTracker
from Users.models.banner_models import Version, LoginEntry, HomeBanner
from Users.models.transactions_models import Transaction
from Users.models.users_models import CustomUser, City, Country, OTP
from unfold.admin import ModelAdmin

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    list_display = ['username', 'name','total_score','month_score', 'formatted_balance']
    search_fields = ['username', 'name', 'email', 'phone']
    list_filter = ['total_score', 'version', 'date_joined']
    fields = ['username', 'name', 'phone', 'email', 'image', 'total_score', 'month_score',
              'balance', 'description']
    def formatted_balance(self,obj):
        return intcomma(obj.balance)
    formatted_balance.short_description = 'balance'
    formatted_balance.admin_order_field = 'balance'


@admin.register(OTP)
class OTPAdmin(ModelAdmin):
    list_display = ['phone','email','otp', 'is_used']
    search_fields = ['phone','email']
    list_filter = ['is_used']
@admin.register(City)
class CityAdmin(ModelAdmin):
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
    def formatted_amount(self,obj):
        return intcomma(obj.amount)
    formatted_amount.short_description = 'amount'
    formatted_amount.admin_order_field = 'amount'
    def formatted_balance_after(self, obj):
        return intcomma(obj.balance_after)

    formatted_balance_after.short_description = 'balance_after'
    formatted_balance_after.admin_order_field = 'balance_after'
    list_display = ['user', 'transaction_type','transaction_status',
                    'payment_gateway','formatted_amount','formatted_balance_after',
                    'tracking_code']
    search_fields = ['user__username','tracking_code','transaction_status', 'transaction_type','payment_gateway']
    list_filter = ['user__username','transaction_type','transaction_status','payment_gateway']


@admin.register(XPTracker)
class XPTrackerAdmin(ModelAdmin):
    list_display = ['user', 'xp','reason','month_xp_after','datetime_created']
    list_filter = ['user__username','reason']
    search_fields = ['user__username','reason', 'datetime_created']



@admin.register(Version)
class VersionAdmin(ModelAdmin):
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
class LoginEntryAdmin(ModelAdmin):
    list_display = (
        'user',
        'created_at',
    )
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'user__phone')
    ordering = ('-created_at',)


@admin.register(HomeBanner)
class HomeBannerAdmin(ModelAdmin):
    list_display = ('id', 'short_message')
    search_fields = ('message','id')

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message

    short_message.short_description = 'Message Preview'
