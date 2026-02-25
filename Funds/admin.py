from django.contrib import admin
from django.contrib.humanize.templatetags.humanize import intcomma
from unfold.admin import ModelAdmin, TabularInline

from Funds.models import FundRaising, FundImage, Donor

class FundImageInline(TabularInline):
    model = FundImage
    extra = 1
    fields = ['image', 'Fund']
from django import forms
from django.contrib import admin
from location_field.forms.plain import PlainLocationField

from .models import FundRaising


class FundRaisingAdminForm(forms.ModelForm):
    # Field فقط برای Admin: نقشه + سرچ، خروجی "lat,lng"
    location = PlainLocationField(
        based_fields=["city"],  # اختیاری؛ اگر City شما text نیست، می‌تونی [] بذاری
        zoom=7,
        required=False,
        initial="35.6892,51.3890",  # پیش‌فرض (تهران)
    )

    class Meta:
        model = FundRaising
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # اگر در حال ادیت رکورد هستیم، location رو از lat/lng پر کن
        if self.instance and self.instance.pk:
            lat = self.instance.latitude
            lng = self.instance.longitude
            if lat is not None and lng is not None:
                self.initial["location"] = f"{lat},{lng}"

    def clean(self):
        cleaned = super().clean()
        loc = cleaned.get("location")

        if loc:
            try:
                lat_str, lng_str = [x.strip() for x in loc.split(",")]
                cleaned["latitude"] = float(lat_str)
                cleaned["longitude"] = float(lng_str)
            except (ValueError, TypeError):
                self.add_error("location", "فرمت لوکیشن معتبر نیست. باید مثل '35.6892,51.3890' باشد.")
        return cleaned

@admin.register(FundRaising)
class FundRaisingAdmin(ModelAdmin):
    form = FundRaisingAdminForm
    def total_amount_comma(self, obj):
        return intcomma(obj.total_amount)
    total_amount_comma.admin_order_field = 'total_amount'
    total_amount_comma.short_description = 'total_amount'
    inlines = [FundImageInline]
    list_display = ['title','total_amount_comma','current_donation','is_available','website']
    list_filter = ['start_date','end_date','is_available','total_amount','current_donation']
    search_fields = ['total_amount', 'title','current_donation']

@admin.register(FundImage)
class FundImage(ModelAdmin):
    list_display = ['image','updated_at','created_at']
    list_filter = ['updated_at','created_at']

@admin.register(Donor)
class DonorAdmin(ModelAdmin):
    def donor_amount(self, obj):
        return intcomma(obj.amount)
    donor_amount.admin_order_field = 'amount'
    donor_amount.short_description = 'amount'
    list_display = ['user','donor_amount','place','datetime','xp']
    list_filter = ['amount','datetime']
    search_fields = ['user__username','amount']