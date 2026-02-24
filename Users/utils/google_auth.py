# auth/utils.py
import time, json, requests
from django.conf import settings
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

class GoogleOIDC:
    @staticmethod
    def verify_id_token(id_token_str: str) -> dict:
        """Verify a Google ID token and return its payload (claims)."""
        req = google_requests.Request()
        claims = google_id_token.verify_oauth2_token(id_token_str, req)
        # issuer
        if claims.get("iss") not in settings.GOOGLE_ISSUERS:
            raise ValueError("Invalid issuer")
        # email
        if not claims.get("email_verified"):
            raise ValueError("Email not verified")
        # audience: allow-list of your client IDs (web/android/ios)
        aud = claims.get("aud")
        azp = claims.get("azp")  # authorized party shows the actual client in multi-aud tokens
        allowed = set(settings.GOOGLE_ALLOWED_CLIENT_IDS)
        if aud not in allowed and (azp and azp not in allowed):
            raise ValueError("Audience not allowed")
        # exp
        if int(claims["exp"]) < int(time.time()):
            raise ValueError("Token expired")
        return claims

    @staticmethod
    def exchange_code_for_tokens(code: str, code_verifier: str, redirect_uri: str) -> dict:
        """Web flow: exchange auth code (with PKCE) for tokens."""
        data = {
            "client_id": settings.GOOGLE_WEB_CLIENT_ID,
            "client_secret": settings.GOOGLE_WEB_CLIENT_SECRET,  # for web app
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        r = requests.post(settings.GOOGLE_TOKEN_ENDPOINT, data=data, timeout=10)
        r.raise_for_status()
        return r.json()
