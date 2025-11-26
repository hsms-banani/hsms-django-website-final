"""
URL configuration for hsms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# hsms_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from seminary.sitemaps import (
    StaticViewSitemap, 
    PageSitemap, 
    NewsSitemap, 
    EventSitemap, 
    PublicationSitemap, 
    FacultySitemap, 
    GallerySitemap
)
from seminary.views import site_map

sitemaps = {
    'static': StaticViewSitemap,
    'pages': PageSitemap,
    'news': NewsSitemap,
    'events': EventSitemap,
    'publications': PublicationSitemap,
    'faculty': FacultySitemap,
    'galleries': GallerySitemap,
}

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('select2/', include('django_select2.urls')),
    path('library/', include('library.urls')), 
    path('api/students/', include('students.api_urls')),
    path('utils/', include('utils.urls')),
    path('students/', include('students.urls')), 
    path('spiritual-food/', include('spiritual_food.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('sitemap/', site_map, name='site_map'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Removed i18n URLs
    path('', include('seminary.urls')),  # Direct include without i18n_patterns
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)