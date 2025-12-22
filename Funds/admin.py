from django.contrib import admin
from unfold.admin import ModelAdmin

from Funds.models import FundRaising, FundImage, Donor

class FundImageInline(admin.TabularInline):
    model = FundImage
    extra = 1
    fields = ['image', 'Fund']

@admin.register(FundRaising)
class FundRaisingAdmin(ModelAdmin):
    inlines = [FundImageInline]
    list_display = ['title','total_amount','current_donation','is_available','website']
    list_filter = ['start_date','end_date','is_available','total_amount','current_donation']
    search_fields = ['is_available','start_date','end_date', 'total_amount', 'title','current_donation']
@admin.register(FundImage)
class FundImage(ModelAdmin):
    list_display = ['image','updated_at','created_at']
    list_filter = ['updated_at','created_at']

@admin.register(Donor)
class DonorAdmin(ModelAdmin):
    list_display = ['user','amount','place','datetime','xp']
    list_filter = ['amount','datetime']
    search_fields = ['amount', 'datetime']