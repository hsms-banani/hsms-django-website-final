# File: seminary/urls.py (Enhanced - without event registration)

from django.urls import path
from . import views

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots_txt'),
    # Home
    path('', views.home, name='home'),
    
    # Our Seminary Section
    path('our-seminary/', views.about_seminary, name='about_seminary'),
    path('our-seminary/rector-welcome/', views.rector_welcome, name='rector_welcome'),
    path('our-seminary/mission-vision/', views.mission_vision, name='mission_vision'),
    path('our-seminary/history/', views.seminary_history, name='seminary_history'),
    path('our-seminary/formation-program/', views.formation_program, name='formation_program'),
    path('our-seminary/rules-regulations/', views.rules_regulations, name='rules_regulations'),
    path('our-seminary/committees/', views.committees, name='committees'),
    
    # History & Heritage Section
    path('history-heritage/', views.history_heritage, name='history_heritage'),
    path('history-heritage/church-history/', views.church_history, name='church_history'),
    path('history-heritage/bangladesh-history/', views.bangladesh_history, name='bangladesh_history'),
    path('history-heritage/local-church-history/', views.local_church_history, name='local_church_history'),
    
    # HSIT Section
    path('hsit/', views.hsit_about, name='hsit_about'),
    path('hsit/director-message/', views.director_message, name='director_message'),
    path('hsit/philosophy-department/', views.philosophy_department, name='philosophy_department'),
    path('hsit/theology-department/', views.theology_department, name='theology_department'),
    path('hsit/faculty/', views.faculty_list, name='faculty_list'),
    path('hsit/faculty/<int:pk>/', views.faculty_detail, name='faculty_detail'),
    path('hsit/academic-calendar/', views.academic_calendar, name='academic_calendar'),
    path('hsit/course-descriptions/', views.course_descriptions, name='course_descriptions'),
    path('hsit/library/', views.library, name='library'),
    path('hsit/student-list/', views.student_list, name='student_list'),
    path('hsit/enrollment-requirements/', views.enrollment_requirements, name='enrollment_requirements'),
    path('hsit/exam-information/', views.exam_information, name='exam_information'),
    path('hsit/tuition-fees/', views.tuition_fees, name='tuition_fees'),
    path('hsit/forms-documents/', views.forms_documents, name='forms_documents'),
    path('hsit/faqs/', views.faqs, name='faqs'),
    
    # Seminary Administration URLs (add these to the "Our Seminary Section")
    path('our-seminary/administration/', views.seminary_administration, name='seminary_administration'),
    path('our-seminary/administration/<int:pk>/', views.administration_detail, name='administration_detail'),

    # Publications Section
    path('publications/', views.publications, name='publications'),
    path('publications/detail/<slug:slug>/', views.publication_detail, name='publication_detail'),
    path('publications/download/<slug:slug>/', views.download_publication, name='download_publication'),
    path('publications/ankur/', views.ankur_publications, name='ankur_publications'),
    path('publications/diptto-sakhyo/', views.diptto_sakhyo_publications, name='diptto_sakhyo_publications'),
    path('publications/prodipon/', views.prodipon_publications, name='prodipon_publications'),

    # News & Events (without registration)
    path('news/', views.news_list, name='news_list'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
    path('events/', views.events_list, name='events_list'),
    path('events/<slug:slug>/', views.event_detail, name='event_detail'),
    
    # Gallery
    path('gallery/', views.gallery_list, name='gallery_list'),
    path('gallery/<slug:slug>/', views.gallery_detail, name='gallery_detail'),
    path('gallery/photos/', views.photo_gallery, name='photo_gallery'),
    path('gallery/videos/', views.video_gallery, name='video_gallery'),
    
    # Contact & Communication
    path('contact/', views.contact, name='contact'),
    
    # Search & HTMX
    path('search/', views.search, name='search'),
    path('api/search/quick/', views.quick_search, name='quick_search'),
    path('load-more/news/', views.load_more_news, name='load_more_news'),
    path('load-more/events/', views.load_more_events, name='load_more_events'),
    
    # API Endpoints
    path('api/announcements/', views.api_announcements, name='api_announcements'),
    path('api/events/upcoming/', views.api_upcoming_events, name='api_upcoming_events'),
    
    # API endpoint for HTMX filtering
    path('api/administration/filter/', views.administration_filter, name='administration_filter'),
    # Utility Pages
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    
    # For SEO RSS Feed
    path('news/rss/', views.NewsFeed(), name='news_rss'),

    
    # Generic page handler (should be last)
    path('<slug:slug>/', views.page_detail, name='page_detail'),
]