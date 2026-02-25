from django.contrib import admin
from django.contrib.humanize.templatetags.humanize import intcomma
from unfold.admin import ModelAdmin
from Ads.models.ads_models import AdSetting, AdCategory, Advertisement, AdEvent


@admin.register(AdSetting)
class AdSettingAdmin(ModelAdmin):
    def intcomma_price_30(self, obj):
        return intcomma(obj.video_price_30)

    intcomma_price_30.admin_order_field = 'video_price_30'
    intcomma_price_30.short_description = 'video_price_30'

    def intcomma_price_60(self, obj):
        return intcomma(obj.video_price_60)

    intcomma_price_60.admin_order_field = 'video_price_60'
    intcomma_price_60.short_description = 'video_price_60'

    def intcomma_price_90(self, obj):
        return intcomma(obj.video_price_90)

    intcomma_price_90.admin_order_field = 'video_price_90'
    intcomma_price_90.short_description = 'video_price_90'

    def intcomma_price_120(self, obj):
        return intcomma(obj.video_price_120)

    intcomma_price_120.admin_order_field = 'video_price_120'
    intcomma_price_120.short_description = 'video_price_120'

    list_display = ["id", "is_available", "intcomma_price_30",
                    "intcomma_price_60", "intcomma_price_90",
                    "intcomma_price_120", "video_xp", "banner_price",
                    "banner_xp", "created_at", "updated_at"]
    search_fields = []
    list_filter = ["is_available", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(AdCategory)
class AdCategoryAdmin(ModelAdmin):
    list_display = ["id", "name", "is_available", "created_at", "updated_at"]
    search_fields = ["name"]
    list_filter = ["is_available", "created_at", "updated_at"]
    ordering = ["name"]


@admin.register(Advertisement)
class AdvertisementAdmin(ModelAdmin):
    def total_click_comma(self, obj):
        return intcomma(obj.total_click)
    total_click_comma.admin_order_field = 'total_click'
    total_click_comma.short_description = 'total_click'
    def total_view_comma(self, obj):
        return intcomma(obj.total_view)
    total_view_comma.admin_order_field = 'total_view'
    total_view_comma.short_description = 'total_view'

    list_display = [
        "id", "title", "status", "user", "city", "category",
        "total_view_comma", "total_click_comma", "website", "created_at", "updated_at",
    ]
    search_fields = ["title", "website", "user__username", "user__email", "user__phone"]
    list_filter = ["status", "city", "category", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(AdEvent)
class AdEventAdmin(ModelAdmin):
    list_display = ["id", "event_type", "user", "ad", "created_at", "updated_at"]
    search_fields = ["user__username", "user__email", "user__phone", "ad__title"]
    list_filter = ["event_type", "created_at", "updated_at"]
    ordering = ["-created_at"]
    raw_id_fields = ["user", "ad"]
