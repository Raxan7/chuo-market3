"""
Sitemap generators for the ChuoSmart platform.
Contains classes for generating sitemaps for products, blogs, talents, and static views.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from .models import Product, Blog
from talents.models import Talent

class ChuoSmartSitemap(Sitemap):
    """Base Sitemap class for ChuoSmart with common settings"""
    protocol = 'https'  # Use HTTPS for better SEO
    
    def get_domain(self, site=None):
        """Override to use the configured SITE_DOMAIN from settings"""
        return settings.SITE_DOMAIN

class ProductSitemap(ChuoSmartSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.all()

    def lastmod(self, obj):
        return obj.created_at if hasattr(obj, 'created_at') else None

    def location(self, obj):
        return reverse('product-detail', kwargs={'slug': obj.slug}) if obj.slug else reverse('product-detail-by-id', args=[obj.pk])


class BlogSitemap(ChuoSmartSitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Blog.objects.all()

    def lastmod(self, obj):
        return obj.created_at if hasattr(obj, 'created_at') else None

    def location(self, obj):
        return reverse('blog_detail', args=[obj.pk])


class TalentSitemap(ChuoSmartSitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Talent.objects.all()

    def lastmod(self, obj):
        return obj.created_at if hasattr(obj, 'created_at') else None

    def location(self, obj):
        return reverse('talent_detail', args=[obj.id])


class StaticViewSitemap(ChuoSmartSitemap):
    priority = 0.7
    changefreq = "daily"

    def items(self):
        return ['home', 'login', 'customerregistration', 'blog_list', 'talent_list', 'lms:lms_home']

    def location(self, item):
        return reverse(item)
