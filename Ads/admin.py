from django.contrib import admin
from unfold.admin import ModelAdmin
from Ads.models.ads_models import AdSetting, AdCategory, Advertisement, AdEvent


@admin.register(AdSetting)
class AdSettingAdmin(ModelAdmin):
    list_display = ["id", "is_available", "video_price", "video_xp", "banner_price", "banner_xp", "created_at", "updated_at"]
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
    list_display = [
        "id", "title", "status", "user", "city", "category",
        "total_view", "total_click", "website", "created_at", "updated_at",
    ]
    search_fields = ["title", "website", "user__username", "user__email", "user__phone"]
    list_filter = ["status", "city", "category", "created_at", "updated_at"]
    ordering = ["-created_at"]
    raw_id_fields = ["user", "city", "category"]


@admin.register(AdEvent)
class AdEventAdmin(ModelAdmin):
    list_display = ["id", "event_type", "user", "ad", "created_at", "updated_at"]
    search_fields = ["user__username", "user__email", "user__phone", "ad__title"]
    list_filter = ["event_type", "created_at", "updated_at"]
    ordering = ["-created_at"]
    raw_id_fields = ["user", "ad"]
