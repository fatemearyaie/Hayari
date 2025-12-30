from django.db import models, transaction

from Users.models import CustomUser


# Create your models here.
class Lottery(models.Model):
    name = models.CharField(max_length=50,null=False, blank=False)
    lottery_datetime = models.DateTimeField(null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            Lottery.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Lottery'
        verbose_name_plural = 'Lotteries'

        indexes = [
            models.Index(fields=['name'], name='lottery_name_idx'),
            models.Index(fields=['lottery_datetime'], name='lottery_datetime_idx'),
        ]
    def __str__(self):
        return self.name

class LotteryRewards(models.Model):
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE)
    place = models.PositiveIntegerField(null=True,blank=True)
    amount = models.DecimalField(max_digits=12,decimal_places=0, null=False, blank=False)
    user = models.ForeignKey(CustomUser, null=True, blank=True,default=None,on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = 'Lottery Reward'
        verbose_name_plural = 'Lottery Rewards'

        indexes = [
            models.Index(fields=['lottery'], name='lottery_idx'),
            models.Index(fields=['amount'], name='lottery_amount_idx'),
            models.Index(fields=['place'], name='lottery_place_idx'),
        ]
    def __str__(self):
        return str(self.amount)