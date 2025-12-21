from rest_framework import serializers

from Users.models.transactions_models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['transaction_id', 'transaction_status', 'description', 'amount',
                  'balance_after', 'tracking_code', 'transaction_type','currency','payment_gateway']