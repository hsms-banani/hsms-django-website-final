# spiritual_food/urls.py
from django.urls import path
from . import views

app_name = 'spiritual_food'

urlpatterns = [
    # Home
    path('', views.spiritual_food_home, name='home'),
    
    # Announcements
    path('announcement/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    
    # Prayer Services
    path('prayer-services/', views.prayer_services, name='prayer_services'),
    
    # Homilies
    path('homilies/', views.HomilyListView.as_view(), name='homily_list'),
    path('homilies/archive/', views.homily_archive, name='homily_archive'),
    path('homilies/<slug:slug>/', views.HomilyDetailView.as_view(), name='homily_detail'),
    
    # Prayer Requests
    path('prayer-request/', views.PrayerRequestCreateView.as_view(), name='prayer_request'),
    path('prayer-request/success/', views.prayer_request_success, name='prayer_request_success'),
    
    # Liturgical Calendar
    path('liturgical-calendar/', views.liturgical_calendar, name='liturgical_calendar'),
    path('spiritual-directors-desk/', views.spiritual_directors_desk, name='spiritual_directors_desk'),
]