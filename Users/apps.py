from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'Users'

    def ready(self):
        import Users.signals.cache_signals
        import Users.signals.transactions_signals
        import Users.signals.xp_singals

