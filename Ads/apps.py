from django.apps import AppConfig


class AdsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Ads'

    def ready(self):
        import Ads.signals.adevent_signal
