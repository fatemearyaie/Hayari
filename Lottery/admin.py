from django.contrib import admin
from django.contrib.humanize.templatetags.humanize import intcomma

from django.db import transaction
from Lottery.models.lottery_models import Lottery, LotteryRewards

from unfold.admin import ModelAdmin, TabularInline


class LotteryRewardsInline(TabularInline):
    model = LotteryRewards
    extra = 0
    ordering = ('place',)

    def formatted_reward(self, obj):
        return intcomma(obj.reward_amount) if obj.reward_amount else "-"

    formatted_reward.short_description = "Reward Amount"



@admin.register(Lottery)
class LotteryAdmin(ModelAdmin):
    list_display = (
        'name',
        'lottery_datetime',
        'is_active',
    )
    list_filter = ('is_active', 'lottery_datetime')
    search_fields = ['name']
    inlines = [LotteryRewardsInline]

@admin.register(LotteryRewards)
class LotteryRewardsAdmin(ModelAdmin):
    def amount_comma(self, obj):
        return intcomma(obj.amount)
    amount_comma.admin_order_field = 'amount'
    amount_comma.short_description = 'amount'

    list_display = (
        'lottery',
        'place',
        'amount_comma',
        'user',
    )
    search_fields = ['user__username', 'lottery__name', 'place']
    list_filter = ('lottery',)
    ordering = ('lottery', 'place')