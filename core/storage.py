"""Storage for private payment evidence.

Files live outside MEDIA_ROOT and are only exposed through the permission-checked
``private_payment_proof`` view.
"""
from django.conf import settings
from django.core.files.storage import FileSystemStorage


private_payment_storage = FileSystemStorage(
    location=settings.PRIVATE_MEDIA_ROOT,
    base_url='/private-payment-proof/',
)
