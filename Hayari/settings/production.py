import os
from decouple import config
from .base import *
from corsheaders.defaults import default_headers

ALLOWED_HOSTS=['46.249.101.76','api.hayari.app','hayari.app','localhost','127.0.0.1','0.0.0.0']


DEBUG = config("DEBUG")
SECRET_KEY = config("SECRET_KEY")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config("POSTGRES_DB"),
        "USER":config("POSTGRES_USER"),
        "PASSWORD":config("POSTGRES_PASSWORD"),
        "HOST":config("POSTGRES_HOST"),
        "PORT":config("POSTGRES_PORT","5432"),
    }
}



CORS_ALLOW_ALL_ORIGINS = False
CSRF_TRUSTED_ORIGINS = [
    'https://hayari.app',
    'https://api.hayari.app',
]
CORS_ALLOW_HEADERS = list(default_headers) + ['x-csrftoken']
