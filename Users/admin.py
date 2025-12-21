from django.contrib import admin

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