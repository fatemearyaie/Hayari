from celery import shared_task
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from celery import shared_task
from Hayari.settings.base import SMS_API_URL, SMS_API_KEY, SMS_SENDER, SMS_PATTERN
import requests
import json

from Hayari.settings.base import DEFAULT_FROM_EMAIL
from smtplib import SMTPConnectError, SMTPServerDisconnected, SMTPDataError
import socket


RETRY_EXC = (socket.timeout, SMTPConnectError, SMTPServerDisconnected, SMTPDataError, OSError)



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



@shared_task(bind=True, name="users.send_otp_pattern")
def send_otp_sms(self, phone, otp):
    headers = {'Content-Type': 'application/json', 'Authorization': SMS_API_KEY}
    body = {
        "sending_type": "pattern",
        "recipients": [phone],
        "from_number": SMS_SENDER,
        "code": SMS_PATTERN,
        "params": {"code": otp}
    }
    r = requests.post(SMS_API_URL, headers=headers, json=body, timeout=15)

    try:
        print("SMS json:", r.json())
    except Exception:
        pass

    r.raise_for_status()
    return r.text
