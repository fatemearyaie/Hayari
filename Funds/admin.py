from django.contrib import admin
from django.contrib.humanize.templatetags.humanize import intcomma
from unfold.admin import ModelAdmin, TabularInline

from Funds.models import FundRaising, FundImage, Donor

class FundImageInline(TabularInline):
    model = FundImage
    extra = 1
    fields = ['image', 'Fund']

@admin.register(FundRaising)
class FundRaisingAdmin(ModelAdmin):
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