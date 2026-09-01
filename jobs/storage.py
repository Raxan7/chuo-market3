"""Private storage for employer verification documents."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage


private_verification_storage = FileSystemStorage(
    location=settings.PRIVATE_MEDIA_ROOT,
    base_url='/jobs/private-verification-documents/',
)
