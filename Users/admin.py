from django.contrib import admin
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
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_available']
    search_fields = ['name', 'is_available']
    list_filter = ['is_available']
    inlines = [CityInline]