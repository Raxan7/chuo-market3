
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import ProductSitemap, BlogSitemap, TalentSitemap, StaticViewSitemap

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
    path('talents/', include('talents.urls')),
    path('chatbot/', include('chatbotapp.urls')),
    path('lms/', include('lms.urls')),
    
    # Sitemap URLs
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
