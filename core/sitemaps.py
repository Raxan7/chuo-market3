from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Blog
from talents.models import Talent

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.all()

    def lastmod(self, obj):
        return obj.created_at if hasattr(obj, 'created_at') else None

    def location(self, obj):
        return reverse('product-detail', args=[obj.pk])


class BlogSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Blog.objects.all()

    def lastmod(self, obj):
        return obj.created_at if hasattr(obj, 'created_at') else None

    def location(self, obj):
        return reverse('blog_detail', args=[obj.slug])


class TalentSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Talent.objects.all()

    def lastmod(self, obj):
        return obj.created_at if hasattr(obj, 'created_at') else None

    def location(self, obj):
        return reverse('talent_detail', args=[obj.id])


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"

    def items(self):
        return ['home', 'login', 'customerregistration', 'blog_list', 'talent_list', 'lms:lms_home']

    def location(self, item):
        return reverse(item)
