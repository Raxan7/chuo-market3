from django.urls import path
from .webhooks import payout_webhook

urlpatterns = [
    path('webhooks/snippe/', payout_webhook, name='payout_webhook'),
]
