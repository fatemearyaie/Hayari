from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication, AuthUser
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import Token

User = get_user_model()

class CacheJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token: Token) -> AuthUser:
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            raise AuthenticationFailed("Token missing user id claim")
        uid = str(user_id)
        key = f"user:obj:{uid}"
        
        user = cache.get(key)
        if user is not None:
            return user
        try:
            user = super().get_user(validated_token)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")
        cache.set(key, user)
        return user