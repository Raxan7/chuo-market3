from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


class Material(models.Model):
    CATEGORY_CHOICES = [
        ('software', 'Software'),
        ('developer_tools', 'Developer Tools'),
        ('education', 'Education'),
        ('productivity', 'Productivity'),
        ('design', 'Design'),
        ('ai_tools', 'AI Tools'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    software_url = models.URLField(max_length=500)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='materials'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('materials:detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        return reverse('materials:update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('materials:delete', kwargs={'pk': self.pk})