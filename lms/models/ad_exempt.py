from django.db import models
from django.contrib.auth.models import User


class AdExemptUser(models.Model):
    """Users who are exempt from seeing ads on the course detail pages"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ad_exemption')
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} (Ad exempt)"
    
    class Meta:
        verbose_name = "Ad Exempt User"
        verbose_name_plural = "Ad Exempt Users"
