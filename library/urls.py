# library/urls.py

from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Main library pages
    path('', views.library_home, name='home'),

    
    path('books/<slug:slug>/', views.book_detail, name='book_detail'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/<slug:slug>/', views.category_books, name='category_books'),
    
    # Authors
    path('authors/', views.author_list, name='author_list'),
    path('authors/<slug:slug>/', views.author_detail, name='author_detail'),
    
    # Publishers
    path('publishers/', views.publisher_list, name='publisher_list'),
    path('publishers/<slug:slug>/', views.publisher_detail, name='publisher_detail'),
    
    path('download-csv-template/', views.download_csv_template, name='download_csv_template'),
    path('upload-csv/', views.upload_csv, name='upload_csv'),

    # HTMX/API endpoints
    path('api/quick-search/', views.quick_search, name='quick_search'),
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('api/load-more-books/', views.load_more_books, name='load_more_books'),
    path('api/get-authors-for-category/', views.get_authors_for_category, name='get_authors_for_category'),
    path('api/search-authors/', views.search_authors, name='search_authors'),
    path('api/search-publishers/', views.search_publishers, name='search_publishers'),
]