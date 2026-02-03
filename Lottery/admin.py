from django.contrib import admin

from django.db import transaction
from Lottery.models.lottery_models import Lottery, LotteryRewards

from unfold.admin import ModelAdmin, TabularInline


class LotteryRewardsInline(TabularInline):
    model = LotteryRewards
    extra = 0
    ordering = ('place',)


@admin.register(Lottery)
class LotteryAdmin(ModelAdmin):
    list_display = (
        'name',
        'lottery_datetime',
        'is_active',
    )
    list_filter = ('is_active', 'lottery_datetime')
    inlines = [LotteryRewardsInline]

@admin.register(LotteryRewards)
class LotteryRewardsAdmin(ModelAdmin):
    list_display = (
        'lottery',
        'place',
        'amount',
        'user',
    )
    list_filter = ('lottery',)
    ordering = ('lottery', 'place')