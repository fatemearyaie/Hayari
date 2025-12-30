from django.contrib import admin

from django.db import transaction
from Lottery.models.lottery_models import Lottery, LotteryRewards

from unfold.admin import ModelAdmin

class LotteryRewardsInline(admin.TabularInline):
    model = LotteryRewards
    extra = 0
    readonly_fields = ('place', 'created_at', 'updated_at')
    ordering = ('place',)


@admin.register(Lottery)
class LotteryAdmin(ModelAdmin):
    list_display = (
        'name',
        'lottery_datetime',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'lottery_datetime')
    readonly_fields = ('created_at', 'updated_at')

    inlines = [LotteryRewardsInline]

@admin.register(LotteryRewards)
class LotteryRewardsAdmin(ModelAdmin):
    list_display = (
        'lottery',
        'place',
        'amount',
        'user',
        'created_at',
    )
    list_filter = ('lottery',)
    ordering = ('lottery', 'place')

    readonly_fields = ('place', 'created_at', 'updated_at')
