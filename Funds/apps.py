from django.apps import AppConfig


class FundsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Funds'

    def ready(self):
        import Funds.signals.funds_signals
        import Funds.signals.cache_signals
