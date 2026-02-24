import os
from datetime import timedelta
from pathlib import Path
from decouple import config
from django.templatetags.static import static
from django.urls import reverse_lazy
from celery.schedules import crontab
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Google OAuth login ---
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")

GOOGLE_ALLOWED_CLIENT_IDS = [
    config("GOOGLE_WEB_CLIENT_ID"),
    config("GOOGLE_ANDROID_CLIENT_ID"),
]
GOOGLE_WEB_CLIENT_ID = config("GOOGLE_WEB_CLIENT_ID")
GOOGLE_WEB_CLIENT_SECRET = config("GOOGLE_WEB_CLIENT_SECRET")  # used only for web code exchange
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}


FIREBASE_SERVICE_ACCOUNT_PATH = config("FIREBASE_SERVICE_ACCOUNT_PATH")

# --- Logging ---
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "default": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },

    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "hayari_errors.log",
            "formatter": "default",
        },
        "console": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },

    "root": {
        "handlers": ["file", "console"],
        "level": "WARNING",
    },
}


INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'corsheaders',

    'Users',
    'Funds',
    'Ads',
    'Notification',
    'Lottery',

]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':
        (
            "Users.services.token_cache.CacheJWTAuthentication",
        ),
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 35,
    'DEFAULT_RENDERER_CLASSES':
        (
        'utils.response_renderer.CustomRenderer',
        ),


    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '10000/day',
        'anon': '1000/day',
        'custom': '500/minute',
    }
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Hayari.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Hayari.wsgi.application'



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')



# --- Redis & Celery (hostnames only) ---
REDIS_URL = "redis://redis:6379/1"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "CONNECTION_POOL_KWARGS": {"max_connections": 200, "retry_on_timeout": True},
                    "SOCKET_TIMEOUT": 1,
                    "SOCKET_CONNECT_TIMEOUT": 1,
                    },
    }
}

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_TASK_TIME_LIMIT = 30
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_IGNORE_RESULT = True


CELERY_BEAT_SCHEDULE = {
    "run_active_lottery_every_minute": {
        "task": "Lottery.tasks.run_active_lottery",
        "schedule": crontab(minute="*"),
    },
    "reset_monthly_scores_first_day": {
        "task": "Users.tasks.reset_monthly_scores",
        "schedule": crontab(minute=0, hour=3, day_of_month=1), # first day of month at 3:00AM
    },
}

AUTH_USER_MODEL = 'Users.CustomUser'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Email credentials from ENV ---
EMAIL_HOST = config('EMAIL_HOST', default='test.com')
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='test@example.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='password')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='test@example.com')
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_TIMEOUT = 15

# --- SMS Panel credentials from ENV ---
SMS_API_URL = config('SMS_API_URL', default='')
SMS_API_KEY = config('SMS_API_KEY', default='')
SMS_SENDER = config('SMS_SENDER', default='')
SMS_PATTERN = config('SMS_PATTERN', default='')


MERCHANT = config('MERCHANT')
SANDBOX = True

UNFOLD = {
    "DASHBOARD_CALLBACK": "Hayari.admin.dashboard.dashboard_context",
    "SCRIPTS": [lambda request: static("admin/js/chart.umd.min.js")],

    "SITE_TITLE": "Hayari",
    "SITE_HEADER": "Hayari",
    "SITE_SUBHEADER": "Operations Console",
    "SITE_URL": "/",

    "THEME": None,
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,


    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Navigation"),
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                        "permission": lambda request: request.user.is_staff,
                    },
                ],
            },
            {
                "title": _("Users"),
                "separator": False,
                "collapsible": True,
                "items": [
                    {
                        "title": _("CustomUsers"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Users_customuser_changelist"),
                    },
                    {
                        "title": _("HomeBanner"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Users_homebanner_changelist"),
                    },
                    {
                        "title": _("OTP"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Users_otp_changelist"),
                    },
                ],
            },
            {
                "title": _("Lottery"),
                "separator": False,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Lottery"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Lottery_lottery_changelist"),
                    },
                ],
            },
            {
                "title": _("Funds"),
                "separator": False,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Fundraising"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Funds_fundraising_changelist"),
                    },
                    {
                        "title": _("Donors"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Funds_donor_changelist"),
                    },

                ],
            },
            {
                "title": _("Ads"),
                "separator": False,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Ads"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Ads_advertisement_changelist"),
                    },
                    {
                        "title": _("AdCategory"),
                        "icon": "table_view",
                        "link": reverse_lazy("admin:Ads_adcategory_changelist"),
                    },

                ],
            },
        ],
    },

}


MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
