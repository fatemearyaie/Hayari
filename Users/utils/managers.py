from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    # normalize phone
    def _normalize_phone(self, phone: str) -> str:
        return phone.strip().replace(" ", "").replace("-", "")
    # normalize email
    def _normalize_email(self, email: str) -> str:
        return self.normalize_email(email).lower()

    def create_user(self, password=None, **extra_fields):
        phone = extra_fields.get("phone")
        email = extra_fields.get("email")

        if not phone and not email:
            raise ValueError(_("Either phone or email must be set."))

        if email:
            email = self._normalize_email(email)
            extra_fields["email"] = email
        if phone:
            phone = self._normalize_phone(phone)
            extra_fields["phone"] = phone

        extra_fields["username"] = extra_fields.get("email") or extra_fields.get("phone")

        user = self.model(**extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not password:
            raise ValueError(_("Superuser must have a password."))


        if not extra_fields.get("phone") and not extra_fields.get("email"):
            u = (extra_fields.get("username") or "").strip()
            if not u:
                raise ValueError(_("Username must be set."))

            if "@" in u:
                extra_fields["email"] = u
            else:
                extra_fields["phone"] = u

        return self.create_user(password=password, **extra_fields)
