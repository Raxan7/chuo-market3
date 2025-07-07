from django.db import models

class SiteSettings(models.Model):
    """
    Model to store site-wide settings
    Implemented as a single-instance model with various configurable settings
    """
    show_ads_before_free_courses = models.BooleanField(
        default=True,
        verbose_name="Show Ads Before Free Courses",
        help_text="When enabled, users will see advertisements before accessing free courses."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return "Site Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create the site settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
