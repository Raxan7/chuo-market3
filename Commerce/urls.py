from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import ProductSitemap, BlogSitemap, TalentSitemap, StaticViewSitemap
from core.views import robots_txt

# Define the sitemaps dictionary
sitemaps = {
    'products': ProductSitemap,
    'blogs': BlogSitemap,
    'talents': TalentSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('affiliates/', include('affiliates.urls')),
    path('talents/', include('talents.urls')),
    path('chatbot/', include('chatbotapp.urls')),
    path('landing/', include('landing.urls')),
    path('lms/', include('lms.urls')),
    path('webpush/', include('webpush.urls')),  # Web Push Notifications
    
    # Sitemap and SEO URLs
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
