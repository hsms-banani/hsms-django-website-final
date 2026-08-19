# seminary/sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Page, News, Event, Publication, Faculty, Gallery

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            'home', 'about_seminary', 'contact', 'rector_welcome', 'mission_vision',
            'seminary_history', 'formation_program', 'rules_regulations',
            'committees', 'history_heritage', 'hsit_about',
            'director_message', 'philosophy_department', 'theology_department',
            'faculty_list', 'academic_calendar', 'library',
            'student_list', 'publications', 'spiritual_food:home', 'news_list', 'events_list',
            'gallery_list', 'terms_of_service',
            'privacy_policy', 'site_map', 'spiritual_food:prayer_services', 'spiritual_food:homily_list',
            'spiritual_food:homily_archive', 'spiritual_food:liturgical_calendar',
            'library:home', 'library:category_list', 'library:author_list', 'library:publisher_list',
        ]

    def location(self, item):
        return reverse(item)

class PageSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Page.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

class NewsSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return News.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

class EventSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Event.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.start_date

class PublicationSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Publication.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.created_at

class FacultySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Faculty.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.joined_date

class GallerySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Gallery.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.created_at