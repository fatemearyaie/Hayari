from celery import shared_task
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.template.loader import render_to_string
from celery import shared_task
from Hayari.settings.base import SMS_API_URL, SMS_API_KEY, SMS_SENDER, SMS_PATTERN
import requests
import json

from Hayari.settings.base import DEFAULT_FROM_EMAIL
from smtplib import SMTPConnectError, SMTPServerDisconnected, SMTPDataError
import socket

from Users.models.users_models import CustomUser

RETRY_EXC_SMS=(socket.timeout,requests.Timeout,requests.ConnectionError,requests.HTTPError,OSError,)
RETRY_EXC=(socket.timeout, SMTPConnectError, SMTPServerDisconnected, SMTPDataError, OSError)



@shared_task(
    bind=True,
    name="users.send_otp_email",
    autoretry_for=RETRY_EXC,
    retry_backoff=5,  # 5s, 10s, 20s, ...
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=6,
)
def send_otp_email(self, email_addr: str, otp_code: str):
    subject = "Hayari Email Verification"
    from_email = DEFAULT_FROM_EMAIL
    to = [email_addr]
    html_content = render_to_string("otp_email.html", {
        "otp_code": otp_code,
    })

    text_content = f"Hi \nYour OTP code is: {otp_code}"

    email = EmailMultiAlternatives(subject, text_content, from_email, to)
    email.attach_alternative(html_content, "text/html")
    email.send()




@shared_task(
    bind=True,
    name="users.send_otp_sms",
    autoretry_for=RETRY_EXC_SMS,
    retry_backoff=5,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=6,
)
def send_otp_sms(self, phone: str, otp: str):
    headers = {"Content-Type": "application/json", "Authorization": SMS_API_KEY}
    body = {
        "sending_type": "pattern",
        "recipients": [phone],
        "from_number": SMS_SENDER,
        "code": SMS_PATTERN,
        "params": {"code": str(otp)},
    }

    r = requests.post(SMS_API_URL, headers=headers, json=body, timeout=15)
    r.raise_for_status()
    data = r.json()

    if not data.get("meta", {}).get("status", False):
        raise RuntimeError(f"SMS provider returned status=false: {data}")

    return data


@shared_task
def reset_monthly_scores():
    with transaction.atomic():
        CustomUser.objects.all().update(month_score=0)
    return {"status": "ok"}