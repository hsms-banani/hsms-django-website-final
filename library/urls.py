# library/urls.py - Enhanced with Borrowing System

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views, views_borrowing

app_name = 'library'

urlpatterns = [
    # Librarian Dashboard
    path('dashboard/', views.librarian_dashboard, name='librarian_dashboard'),

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
    
    # CSV Import/Export
    path('download-csv-template/', views.download_csv_template, name='download_csv_template'),
    path('upload-csv/', views.upload_csv, name='upload_csv'),

    # Borrowing System
    path('my-books/', views_borrowing.my_borrowed_books, name='my_borrowed_books'),
    path('borrow/<slug:slug>/', views_borrowing.borrow_book, name='borrow_book'),
    path('renew/<int:record_id>/', views_borrowing.renew_book, name='renew_book'),
    path('return/<int:record_id>/', views_borrowing.return_book, name='return_book'),
    path('borrow-history/', views_borrowing.borrow_history, name='borrow_history'),

    # HTMX/API endpoints
    path('api/quick-search/', views.quick_search, name='quick_search'),
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('api/load-more-books/', views.load_more_books, name='load_more_books'),
    path('api/get-authors-for-category/', views.get_authors_for_category, name='get_authors_for_category'),
    path('api/search-authors/', views.search_authors, name='search_authors'),
    path('api/search-publishers/', views.search_publishers, name='search_publishers'),

    # Dashboard partials
    path('api/get-all-books-table/', views.get_all_books_table, name='get_all_books_table'),
    path('api/get-borrowed-books-table/', views.get_borrowed_books_table, name='get_borrowed_books_table'),
    path('api/get-overdue-books-table/', views.get_overdue_books_table, name='get_overdue_books_table'),
    path('api/get-returned-books-table/', views.get_returned_books_table, name='get_returned_books_table'),
    path('api/get-dashboard-content/', views.get_dashboard_content, name='get_dashboard_content'),

    # Book management
    path('dashboard/edit-book/<int:book_id>/', views.edit_book, name='edit_book'),
    path('dashboard/delete-book/<int:book_id>/', views.delete_book, name='delete_book'),

    # Borrow record management
    path('dashboard/borrow-record/<int:record_id>/', views.borrow_record_detail, name='borrow_record_detail'),
    path('dashboard/send-reminder/<int:record_id>/', views.send_reminder, name='send_reminder'),
    path('dashboard/add-book/', views.add_book, name='add_book'),

    # Reporting
    path('dashboard/generate-report/<str:report_type>/', views.generate_report, name='generate_report'),

    # Manual actions from dashboard
    path('dashboard/renew-book/<int:record_id>/', views.dashboard_renew_book, name='dashboard_renew_book'),
    path('dashboard/return-book/<int:record_id>/', views.dashboard_return_book, name='dashboard_return_book'),
    path('dashboard/mark-as-paid/<int:record_id>/', views.dashboard_mark_as_paid, name='dashboard_mark_as_paid'),
    path('dashboard/download-returned-csv/', views.download_returned_books_csv, name='download_returned_books_csv'),

    # Password reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset/password_reset_form.html',
        email_template_name='registration/password_reset/password_reset_email.html',
        subject_template_name='registration/password_reset/password_reset_subject.txt',
        success_url=reverse_lazy('library:password_reset_done')
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset/password_reset_confirm.html',
        success_url=reverse_lazy('library:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset/password_reset_complete.html'
    ), name='password_reset_complete'),
]