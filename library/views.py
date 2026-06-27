# library/views.py - Enhanced with Bangla/Multilingual Support

from django.shortcuts import render, get_object_or_404, redirect
from django.db import connections
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Case, When, Prefetch, Sum, Avg, Q, F
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.core.cache import cache
import json
from functools import reduce
import operator
from thefuzz import process
from thefuzz import fuzz
import re
import unicodedata
from .models import Book, Category, Author, Publisher, BookSearch, BorrowRecord, Periodical
from .forms import BookForm
from .email_service import LibraryEmailService
from django.contrib.auth.models import User
from django.views.decorators.cache import cache_page
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.contrib import messages
import csv
import hashlib
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

# Cache timeouts
CACHE_TIMEOUT_SHORT = 60 * 5   # 5 minutes
CACHE_TIMEOUT_MEDIUM = 60 * 15  # 15 minutes
CACHE_TIMEOUT_LONG = 60 * 60    # 1 hour

def detect_text_language(text):
    """Detect if text contains Bangla characters"""
    if not text:
        return 'en'
    
    bangla_pattern = re.compile(r'[\u0980-\u09FF]')
    english_pattern = re.compile(r'[A-Za-z]')
    
    has_bangla = bangla_pattern.search(text)
    has_english = english_pattern.search(text)
    
    if has_bangla and has_english:
        return 'mixed'
    elif has_bangla:
        return 'bn'
    return 'en'

def normalize_search_query(query):
    """Normalize search query for better matching"""
    if not query:
        return ""
    
    # Normalize Unicode (important for Bangla)
    query = unicodedata.normalize('NFC', query.strip())
    
    # Remove extra whitespace
    query = ' '.join(query.split())
    
    return query

def get_optimized_book_queryset():
    """Get optimized book queryset with all relations prefetched"""
    return Book.objects.select_related(
        'publisher', 
        'category'
    ).prefetch_related(
        Prefetch('authors', queryset=Author.objects.only(
            'id', 'first_name', 'last_name', 'first_name_bangla', 
            'last_name_bangla', 'slug', 'primary_language'
        ))
    ).only(
        'id', 'title', 'title_bangla', 'subtitle', 'subtitle_bangla', 
        'slug', 'publication_year', 'isbn_10', 'isbn_13', 'call_number', 
        'keywords', 'keywords_bangla', 'language', 'status', 'copies_available', 
        'total_copies', 'times_borrowed', 'created_at', 'cover_image', 
        'classification_number', 'cutter_number',
        'publisher__name', 'publisher__slug',
        'category__name', 'category__slug'
    )

def download_csv_template(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="book_import_template.csv"'
    
    # Add BOM for Excel compatibility with Unicode
    response.write('\ufeff')

    writer = csv.writer(response)
    
    # ✅ FIXED: Added accession_number and volume
    header = [
        'title*', 'title_bangla', 'subtitle', 'subtitle_bangla', 
        'accession_number*',  # ✅ ADDED
        'volume',              # ✅ ADDED
        'author*', 
        'publisher*', 'publication_year*', 'isbn_10', 'isbn_13', 
        'classification_number*', 'cutter_number*', 'category*', 'language', 
        'pages', 'edition', 'description', 'description_bangla',
        'keywords', 'keywords_bangla', 'total_copies', 'copies_available', 
        'location_shelf', 'status'
    ]
    writer.writerow(header)
    
    # ✅ FIXED: Updated sample data
    writer.writerow([
        'Sample Book Title', 'নমুনা বই শিরোনাম', 'A Sample Subtitle', 'একটি নমুনা উপশিরোনাম',
        'ACC-2024-001',  # ✅ ADDED - Accession number
        'v1',            # ✅ ADDED - Volume
        'Author One;Author Two', 'Sample Publisher', '2023',
        '1234567890', '9781234567890', '230.1', 'S64i', 'Systematic Theology', 'bn', '450', 
        '3rd Edition', 'A sample book description.', 'একটি নমুনা বই বর্ণনা।',
        'theology,christianity,doctrine', 'ধর্মতত্ত্ব,খ্রিস্টধর্ম,মতবাদ', 
        '3', '2', 'A-1-5', 'available'
    ])

    return response

@staff_member_required
def upload_csv(request):
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            fs = FileSystemStorage(location='media/library/csv_uploads')
            filename = fs.save(csv_file.name, csv_file)
            file_path = fs.path(filename)
            
            import io
            out = io.StringIO()
            err = io.StringIO()
            import_log = ""
            try:
                # Use the enhanced import command with encoding detection
                call_command('import_books', file_path, '--no-color', stdout=out, stderr=err)
                import_log = out.getvalue()
                messages.success(request, f'Successfully imported books from {filename}. See log below for details.')
            except Exception as e:
                import_log = out.getvalue()
                if err.getvalue():
                    import_log += "\nErrors:\n" + err.getvalue()
                if not import_log:
                    import_log = f'Exception: {str(e)}'
                messages.warning(request, f'Import finished with errors. See log below for details.')
            
            return render(request, 'library/upload_csv.html', {'import_log': import_log})
        else:
            messages.error(request, 'No CSV file selected.')

    return render(request, 'library/upload_csv.html')

def _get_filtered_sorted_books(request):
    """
    Enhanced filtering with multilingual support
    """
    books = get_optimized_book_queryset()
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', '-created_at')
    using_postgres = connections['default'].vendor == 'postgresql'
    
    # Normalize query for better search
    query = normalize_search_query(query)

    # --- Multilingual Search ---
    if query:
        query_language = detect_text_language(query)
        
        if using_postgres:
            # Enhanced PostgreSQL search with unified multilingual support
            search_vector = (
                SearchVector('title', weight='A') + 
                SearchVector('title_bangla', weight='A') +
                SearchVector('subtitle', weight='B') +
                SearchVector('subtitle_bangla', weight='B') +
                SearchVector('authors__first_name', weight='B') +
                SearchVector('authors__last_name', weight='B') +
                SearchVector('authors__first_name_bangla', weight='B') +
                SearchVector('authors__last_name_bangla', weight='B') +
                SearchVector('keywords', weight='C') +
                SearchVector('keywords_bangla', weight='C') +
                SearchVector('isbn_10', weight='D') +
                SearchVector('isbn_13', weight='D') +
                SearchVector('call_number', weight='D')
            )
            
            search_query = SearchQuery(query)
            books = books.annotate(
                rank=SearchRank(search_vector, search_query)
            ).filter(rank__gte=0.1)
        else:
            # Enhanced SQLite search with multilingual support
            query_words = query.split()
            final_q = Q()
            
            for word in query_words:
                word_q = (
                    Q(title__icontains=word) | Q(title_bangla__icontains=word) |
                    Q(subtitle__icontains=word) | Q(subtitle_bangla__icontains=word) |
                    Q(authors__first_name__icontains=word) | Q(authors__last_name__icontains=word) |
                    Q(authors__first_name_bangla__icontains=word) | Q(authors__last_name_bangla__icontains=word) |
                    Q(isbn_10__icontains=word) | Q(isbn_13__icontains=word) |
                    Q(keywords__icontains=word) | Q(keywords_bangla__icontains=word) |
                    Q(call_number__icontains=word) |
                    Q(publisher__name__icontains=word) | Q(category__name__icontains=word)
                )
                final_q &= word_q
            
            if final_q:
                books = books.filter(final_q).distinct()
            else:
                books = books.none()

        # Track search with language detection
        try:
            search_obj, created = BookSearch.objects.get_or_create(
                query=query,
                defaults={'language_detected': query_language}
            )
            if not created:
                search_obj.search_count += 1
                search_obj.save(update_fields=['search_count', 'last_searched'])
        except:
            pass

    # --- Enhanced Filtering ---
    category_slug = request.GET.get('category')
    if category_slug:
        books = books.filter(category__slug=category_slug)

    # Language filter
    language = request.GET.get('language')
    if language:
        books = books.filter(language=language)

    author_slug = request.GET.get('author')
    author_q = request.GET.get('author_q')
    if author_slug:
        books = books.filter(authors__slug=author_slug)
    elif author_q:
        author_q = normalize_search_query(author_q)
        author_lang = detect_text_language(author_q)
        
        if author_lang in ['bn', 'mixed']:
            books = books.filter(
                Q(authors__first_name__icontains=author_q) | 
                Q(authors__last_name__icontains=author_q) |
                Q(authors__first_name_bangla__icontains=author_q) | 
                Q(authors__last_name_bangla__icontains=author_q)
            ).distinct()
        else:
            books = books.filter(
                Q(authors__first_name__icontains=author_q) | 
                Q(authors__last_name__icontains=author_q)
            ).distinct()

    publisher_slug = request.GET.get('publisher')
    publisher_q = request.GET.get('publisher_q')
    if publisher_slug:
        books = books.filter(publisher__slug=publisher_slug)
    elif publisher_q:
        publisher_q = normalize_search_query(publisher_q)
        books = books.filter(publisher__name__icontains=publisher_q)

    status = request.GET.get('status')
    if status:
        if status == 'available':
            books = books.filter(status='available', copies_available__gt=0)
        else:
            books = books.filter(status=status)

    # --- Sorting ---
    valid_sorts = [
        'title', '-title', '-publication_year', 'publication_year', 
        '-times_borrowed', 'times_borrowed', '-created_at', 'created_at', 
        'call_number', '-call_number', 'language', '-language'
    ]
    if query and using_postgres:
        valid_sorts.append('relevance')
        if sort_by == '-created_at':  # Default sort for search should be relevance
            sort_by = 'relevance'

    if sort_by == 'relevance' and 'rank' in books.query.annotations:
        books = books.order_by('-rank', '-created_at')
    elif sort_by in valid_sorts:
        books = books.order_by(sort_by)
    
    return books

def library_home(request):
    """Enhanced home view with multilingual support"""
    books = _get_filtered_sorted_books(request)

    paginator = Paginator(books, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options with language-aware caching
    user_language = request.GET.get('language', 'all')
    filter_options = cache.get(f'library_filter_options_v3_{user_language}')
    if not filter_options:
        categories = Category.objects.annotate(
            publication_count=Count('book_publications') + Count('periodical_publications')
        ).filter(publication_count__gt=0).only('id', 'name', 'name_bangla', 'slug').order_by('name')
        
        filter_options = {
            'categories': categories,
            'languages': Book.LANGUAGE_CHOICES,
        }
        cache.set(f'library_filter_options_v3_{user_language}', filter_options, CACHE_TIMEOUT_LONG)

    # Handle search box state after form submission
    author_q_value = request.GET.get('author_q', '')
    if request.GET.get('author') and not author_q_value:
        try:
            author = Author.objects.get(slug=request.GET.get('author'))
            # Choose appropriate name based on content language
            if author.full_name_bangla:
                author_q_value = author.full_name_bangla
            else:
                author_q_value = author.full_name
        except Author.DoesNotExist:
            pass

    publisher_q_value = request.GET.get('publisher_q', '')
    if request.GET.get('publisher') and not publisher_q_value:
        try:
            publisher = Publisher.objects.get(slug=request.GET.get('publisher'))
            publisher_q_value = publisher.name
        except Publisher.DoesNotExist:
            pass

    context = {
        'page_obj': page_obj,
        'filter_options': filter_options,
        'selected_filters': {
            'category': request.GET.get('category'),
            'author': request.GET.get('author'),
            'publisher': request.GET.get('publisher'),
            'status': request.GET.get('status'),
            'language': request.GET.get('language'),
        },
        'search_query': request.GET.get('q', '').strip(),
        'sort_by': request.GET.get('sort', '-created_at'),
        'author_q_value': author_q_value,
        'publisher_q_value': publisher_q_value,
        'detected_language': detect_text_language(request.GET.get('q', '')),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'library/partials/book_grid.html', context)

    return render(request, 'library/home.html', context)

def book_detail(request, slug):
    """Enhanced book detail view with multilingual content"""
    cache_key = f"book_detail_{slug}"
    context = cache.get(cache_key)
    
    if context is None:
        book = get_object_or_404(
            Book.objects.select_related('publisher', 'category')
                       .prefetch_related('authors'), 
            slug=slug
        )
        
        # Find related books with multilingual consideration
        related_books = Book.objects.filter(
            Q(category=book.category) | 
            Q(authors__in=book.authors.all()) |
            Q(language=book.language)  # Same language books
        ).exclude(id=book.id).distinct().select_related(
            'publisher', 'category'
        ).prefetch_related('authors').only(
            'id', 'title', 'title_bangla', 'slug', 'call_number', 'status', 
            'copies_available', 'total_copies', 'cover_image', 'language',
            'publisher__name', 'category__name'
        )[:6]
        
        context = {
            'book': book,
            'related_books': list(related_books),
            'book_language': book.language,
            'is_multilingual': bool(book.title_bangla or book.description_bangla),
        }
        
        cache.set(cache_key, context, CACHE_TIMEOUT_MEDIUM)
    
    return render(request, 'library/book_detail.html', context)

@require_http_methods(["GET"])
def quick_search(request):
    """
    Ultra-fast quick search with single character support
    Optimized with aggressive caching and minimal queries
    """
    query = request.GET.get('q', '').strip()
    
    # Return empty for no input
    if len(query) < 1:
        return render(request, 'library/partials/quick_search_results.html', 
                     {'results': [], 'query': query})
    
    # Normalize query
    query = normalize_search_query(query)
    query_language = detect_text_language(query)
    
    # Create cache key based on query and language
    cache_key = f"quick_search_v2_{hashlib.md5(f'{query}_{query_language}'.encode()).hexdigest()}"
    
    # Try to get from cache first (30 second cache for super fast responses)
    results = cache.get(cache_key)
    
    if results is None:
        # Build optimized queryset
        books = Book.objects.select_related('publisher', 'category').prefetch_related(
            Prefetch('authors', queryset=Author.objects.only(
                'id', 'first_name', 'last_name', 'first_name_bangla', 
                'last_name_bangla', 'slug'
            ))
        ).only(
            'id', 'title', 'title_bangla', 'slug', 'isbn_10', 'isbn_13', 
            'call_number', 'status', 'copies_available', 'total_copies', 
            'language', 'times_borrowed', 'cover_image', 'location_shelf',
            'publication_year', 'subtitle', 'subtitle_bangla',
            'publisher__name', 'category__name'
        )
        
        # For single character, use more targeted search
        if len(query) == 1:
            # Single character - search only in titles and call numbers for performance
            if query_language in ['bn', 'mixed']:
                search_q = (
                    Q(title__istartswith=query) | 
                    Q(title_bangla__istartswith=query) |
                    Q(call_number__istartswith=query)
                )
            else:
                search_q = (
                    Q(title__istartswith=query) | 
                    Q(call_number__istartswith=query)
                )
            
            # Limit to 15 results for single char
            books = books.filter(search_q)[:15]
            
        else:
            # Multi-character search - more comprehensive
            db_results = optimized_multilingual_search(books, query, query_language)
            books = [book for book, score in db_results[:12]]
        
        results = list(books)
        
        # Cache for 30 seconds (fast responses for repeated searches)
        cache.set(cache_key, results, 30)
    
    return render(request, 'library/partials/quick_search_results.html', {
        'results': results, 
        'query': query,
        'query_language': query_language,
        'is_single_char': len(query) == 1,
    })

def optimized_multilingual_search(books, query, query_language):
    """
    Enhanced search with better performance for short queries
    """
    using_postgres = connections['default'].vendor == 'postgresql'
    
    if using_postgres:
        # PostgreSQL full-text search
        if query_language in ['bn', 'mixed']:
            search_vector = (
                SearchVector('title', weight='A') + 
                SearchVector('title_bangla', weight='A') +
                SearchVector('authors__first_name', weight='B') +
                SearchVector('authors__last_name', weight='B') +
                SearchVector('authors__first_name_bangla', weight='B') +
                SearchVector('authors__last_name_bangla', weight='B') +
                SearchVector('isbn_10', weight='C') +
                SearchVector('isbn_13', weight='C') +
                SearchVector('call_number', weight='D')
            )
        else:
            search_vector = (
                SearchVector('title', weight='A') + 
                SearchVector('authors__first_name', weight='B') +
                SearchVector('authors__last_name', weight='B') + 
                SearchVector('isbn_10', weight='C') +
                SearchVector('isbn_13', weight='C') +
                SearchVector('call_number', weight='D')
            )
        
        search_query = SearchQuery(query)
        
        books_with_rank = books.annotate(
            rank=SearchRank(search_vector, search_query)
        ).filter(rank__gte=0.05).order_by('-rank')  # Lower threshold for short queries
        
        return [(book, float(book.rank) * 100) for book in books_with_rank[:15]]
    
    else:
        # SQLite fallback with optimized scoring
        query_lower = query.lower()
        scored_books = []
        
        # Build efficient Q objects
        if query_language in ['bn', 'mixed']:
            q_filter = (
                Q(title__icontains=query) |
                Q(title_bangla__icontains=query) |
                Q(authors__first_name__icontains=query) |
                Q(authors__last_name__icontains=query) |
                Q(authors__first_name_bangla__icontains=query) |
                Q(authors__last_name_bangla__icontains=query) |
                Q(isbn_10__icontains=query) |
                Q(isbn_13__icontains=query) |
                Q(call_number__icontains=query)
            )
        else:
            q_filter = (
                Q(title__istartswith=query) |  # Prioritize starts-with
                Q(title__icontains=query) |
                Q(authors__first_name__icontains=query) |
                Q(authors__last_name__icontains=query) |
                Q(isbn_10__icontains=query) |
                Q(isbn_13__icontains=query) |
                Q(call_number__istartswith=query)
            )
        
        filtered_books = books.filter(q_filter).distinct()[:25]
        
        # Score the results
        for book in filtered_books:
            score = 0
            title_lower = book.title.lower()
            title_bangla_lower = (book.title_bangla or '').lower()
            
            # Exact match bonus
            if query_lower == title_lower or query_lower == title_bangla_lower:
                score += 200
            
            # Starts with bonus (high priority)
            if title_lower.startswith(query_lower):
                score += 150
            elif title_bangla_lower.startswith(query_lower):
                score += 150
            
            # Contains in title
            if query_lower in title_lower:
                score += 80
            if query_lower in title_bangla_lower:
                score += 80
            
            # Call number match (exact or starts with)
            call_number_lower = (book.call_number or '').lower()
            if query_lower == call_number_lower:
                score += 120
            elif call_number_lower.startswith(query_lower):
                score += 100
            elif query_lower in call_number_lower:
                score += 60
            
            # ISBN match
            if book.isbn_10 and query in book.isbn_10:
                score += 90
            if book.isbn_13 and query in book.isbn_13:
                score += 90
            
            # Author match
            for author in book.authors.all():
                author_full = f"{author.first_name} {author.last_name}".lower()
                author_full_bangla = f"{author.first_name_bangla} {author.last_name_bangla}".lower()
                
                if query_lower in author_full or query_lower in author_full_bangla:
                    score += 70
            
            # Language match bonus
            if book.language == query_language:
                score += 15
            
            # Popularity bonus (slight)
            if book.times_borrowed > 10:
                score += 10
            elif book.times_borrowed > 5:
                score += 5
            
            if score > 0:
                scored_books.append((book, score))
        
        # Sort by score descending
        return sorted(scored_books, key=lambda x: x[1], reverse=True)

def search_authors(request):
    """Enhanced author search with multilingual support"""
    query = request.GET.get('author_q', '').strip()
    if len(query) >= 1:
        query = normalize_search_query(query)
        query_language = detect_text_language(query)
        
        if query_language in ['bn', 'mixed']:
            authors = Author.objects.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query) |
                Q(first_name_bangla__icontains=query) | Q(last_name_bangla__icontains=query)
            ).annotate(publication_count=Count('publications')).order_by('-publication_count')[:10]
        else:
            authors = Author.objects.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).annotate(publication_count=Count('publications')).order_by('-publication_count')[:10]
    
    return render(request, 'library/partials/_author_search_results.html', {
        'authors': authors,
        'query_language': detect_text_language(query) if query else 'en'
    })

def search_publishers(request):
    """Enhanced publisher search"""
    query = request.GET.get('publisher_q', '').strip()
    publishers = []
    if len(query) >= 1:
        query = normalize_search_query(query)
        publishers = (
            Publisher.objects.filter(name__icontains=query)
            .annotate(publication_count=Count('publications'))
            .order_by('-publication_count')[:10]
        )
    
    return render(request, 'library/partials/_publisher_search_results.html', {
        'publishers': publishers
    })

# Keep existing view functions but with minimal updates for better caching
@cache_page(CACHE_TIMEOUT_LONG)
def category_list(request):
    """Display all categories with multilingual names"""
    categories = Category.objects.annotate(
        publication_count=Count('book_publications') + Count('periodical_publications')
    ).only('id', 'name', 'name_bangla', 'slug', 'description', 'description_bangla').order_by('name')
    
    return render(request, 'library/category_list.html', {
        'categories': categories
    })

def category_books(request, slug):
    """Display books in a specific category"""
    category = get_object_or_404(Category.objects.only('id', 'name', 'name_bangla', 'slug'), slug=slug)
    
    books = get_optimized_book_queryset().filter(category=category)
    
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('HX-Request'):
        return render(request, 'library/partials/generic_load_more.html', {
            'page_obj': page_obj
        })
    
    return render(request, 'library/category_books.html', {
        'category': category,
        'page_obj': page_obj
    })

@cache_page(CACHE_TIMEOUT_LONG)
def author_list(request):
    """Display all authors with multilingual names"""
    authors = Author.objects.annotate(
        publication_count=Count('publications')
    ).only(
        'id', 'first_name', 'last_name', 'first_name_bangla', 
        'last_name_bangla', 'slug', 'bio', 'bio_bangla', 'primary_language'
    ).order_by('last_name', 'first_name')
    
    paginator = Paginator(authors, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/author_list.html', {
        'page_obj': page_obj
    })

def author_detail(request, slug):
    """Display author details and their books with multilingual support"""
    author = get_object_or_404(
        Author.objects.only(
            'id', 'first_name', 'last_name', 'first_name_bangla', 
            'last_name_bangla', 'slug', 'bio', 'bio_bangla', 'primary_language'
        ), 
        slug=slug
    )
    
    books = get_optimized_book_queryset().filter(authors=author)
    
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('HX-Request'):
        return render(request, 'library/partials/generic_load_more.html', {
            'page_obj': page_obj
        })
    
    return render(request, 'library/author_detail.html', {
        'author': author,
        'page_obj': page_obj
    })

def publisher_list(request):
    """Display all publishers with multilingual names"""
    publishers = cache.get('library_publisher_list_v2')
    if not publishers:
        publishers = Publisher.objects.annotate(
            publication_count=Count('publications')
        ).only('id', 'name', 'name_bangla', 'slug').order_by('name')
        cache.set('library_publisher_list_v2', publishers, CACHE_TIMEOUT_MEDIUM)

    paginator = Paginator(publishers, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/publisher_list.html', {
        'page_obj': page_obj,
    })

def publisher_detail(request, slug):
    """Display publisher details and their books"""
    publisher = get_object_or_404(
        Publisher.objects.only('id', 'name', 'name_bangla', 'slug', 'address', 'website'), 
        slug=slug
    )
    books = Book.objects.filter(publisher=publisher).select_related('publisher', 'category').prefetch_related('authors')
    
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('HX-Request'):
        return render(request, 'library/partials/generic_load_more.html', {
            'page_obj': page_obj
        })
    
    return render(request, 'library/publisher_detail.html', {
        'publisher': publisher,
        'page_obj': page_obj,
    })

# Enhanced HTMX Views
@require_http_methods(["GET"])
def load_more_books(request):
    """Load more books for infinite scroll with multilingual support"""
    books = _get_filtered_sorted_books(request)
    paginator = Paginator(books, 16)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/partials/load_more_response.html', {
        'page_obj': page_obj
    })

def search_suggestions(request):
    """Enhanced search suggestions with multilingual support"""
    query = request.GET.get('q', '').strip()
    if len(query) < 1:
        return render(request, 'library/partials/search_suggestions.html', {'suggestions': []})

    query = normalize_search_query(query)
    query_language = detect_text_language(query)
    query_words = query.split()

    # Build query based on detected language
    q_objects = []
    for word in query_words:
        if query_language in ['bn', 'mixed']:
            q_objects.append(
                Q(title__icontains=word) | Q(title_bangla__icontains=word)
            )
        else:
            q_objects.append(Q(title__icontains=word))

    if q_objects:
        # Get both English and Bangla titles
        suggestions = []
        books = Book.objects.filter(reduce(operator.and_, q_objects))
        
        for book in books.distinct()[:10]:
            if query_language == 'bn' and book.title_bangla:
                suggestions.append(book.title_bangla)
            elif book.title:
                suggestions.append(book.title)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
    else:
        unique_suggestions = []
    
    return render(request, 'library/partials/search_suggestions.html', {
        'suggestions': unique_suggestions[:8],  # Limit to 8 suggestions
        'query_language': query_language
    })

def get_authors_for_category(request):
    """Get authors for category with multilingual support"""
    category_slug = request.GET.get('category')
    authors = Author.objects.all()
    if category_slug:
        authors = authors.filter(publications__category__slug=category_slug).distinct()
    
    authors = authors.order_by('last_name', 'first_name')
    
    return render(request, 'library/partials/author_options.html', {
        'authors': authors
    })

def librarian_dashboard(request):
    """Enhanced dashboard with comprehensive statistics and charts"""
    
    # Basic Stats
    total_publications = Book.objects.count() + Periodical.objects.count()
    total_books = Book.objects.count()
    total_periodicals = Periodical.objects.count()
    
    # Borrowing Stats
    active_borrows = BorrowRecord.objects.filter(status__in=['active', 'overdue'])
    borrowed_books_count = active_borrows.count()
    overdue_books_count = BorrowRecord.objects.filter(status='overdue').count()
    
    # User Stats
    total_users = User.objects.filter(is_staff=False).count()
    active_borrowers = BorrowRecord.objects.filter(
        status__in=['active', 'overdue']
    ).values('borrower').distinct().count()
    
    # Financial Stats
    total_fines = BorrowRecord.objects.filter(
        fine_amount__gt=0
    ).aggregate(total=Sum('fine_amount'))['total'] or 0
    
    unpaid_fines = BorrowRecord.objects.filter(
        fine_amount__gt=0,
        fine_paid=False
    ).aggregate(total=Sum('fine_amount'))['total'] or 0
    
    paid_fines = total_fines - unpaid_fines
    
    # Recent Activity
    recent_borrows = BorrowRecord.objects.prefetch_related(
        'borrower', 'publication'
    ).order_by('-borrow_date')[:10]
    
    recent_returns = BorrowRecord.objects.filter(
        status='returned'
    ).prefetch_related(
        'borrower', 'publication'
    ).order_by('-return_date')[:10]
    
    # Popular Books
    popular_books = Book.objects.filter(
        times_borrowed__gt=0
    ).order_by('-times_borrowed')[:10]
    
    # Books that need attention (low availability)
    low_stock_books = Book.objects.filter(
        copies_available__lte=1,
        copies_available__gt=0,
        total_copies__gt=1
    ).order_by('copies_available')[:10]
    
    # Borrowing trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_borrows = BorrowRecord.objects.filter(
        borrow_date__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('borrow_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Category distribution
    category_stats = Category.objects.annotate(
        book_count=Count('book_publications')
    ).order_by('-book_count')[:10]
    
    # Users with most borrows
    top_borrowers = User.objects.filter(
        is_staff=False
    ).annotate(
        borrow_count=Count('borrowed_record__id')
    ).filter(borrow_count__gt=0).order_by('-borrow_count')[:10]
    
    # Due date alerts
    due_soon = BorrowRecord.objects.filter(
        status='active',
        due_date__lte=timezone.now().date() + timedelta(days=3),
        due_date__gte=timezone.now().date()
    ).prefetch_related('borrower', 'publication').order_by('due_date')
    
    context = {
        # Basic stats
        'total_publications': total_publications,
        'total_books': total_books,
        'total_periodicals': total_periodicals,
        'borrowed_books_count': borrowed_books_count,
        'overdue_books_count': overdue_books_count,
        'total_users': total_users,
        'active_borrowers': active_borrowers,
        
        # Financial stats
        'total_fines': total_fines,
        'unpaid_fines': unpaid_fines,
        'paid_fines': paid_fines,
        
        # Recent activity
        'recent_borrows': recent_borrows,
        'recent_returns': recent_returns,
        'due_soon': due_soon,
        
        # Analysis
        'popular_books': popular_books,
        'low_stock_books': low_stock_books,
        'category_stats': category_stats,
        'top_borrowers': top_borrowers,
        'daily_borrows': daily_borrows,
        
        # For navigation
        'active_tab': 'dashboard',
    }
    
    return render(request, 'library/librarian_dashboard.html', context)

@staff_member_required
def get_all_books_table(request):
    all_books_list = Book.objects.all().order_by('-created_at')
    paginator = Paginator(all_books_list, 10)
    page_number = request.GET.get('page')
    all_books = paginator.get_page(page_number)
    return render(request, 'library/partials/_all_books_table.html', {'all_books': all_books})

@staff_member_required
def get_borrowed_books_table(request):
    query = request.GET.get('q')
    borrowed_records = BorrowRecord.objects.filter(
        status__in=['active', 'overdue']
    ).select_related('borrower').prefetch_related('publication').order_by('-due_date')

    if query:
        book_type = ContentType.objects.get_for_model(Book)
        periodical_type = ContentType.objects.get_for_model(Periodical)

        book_q = Q(
            content_type=book_type,
            object_id__in=Book.objects.filter(Q(title__icontains=query) | Q(accession_number__icontains=query) | Q(call_number__icontains=query)).values('id')
        )
        periodical_q = Q(
            content_type=periodical_type,
            object_id__in=Periodical.objects.filter(Q(title__icontains=query) | Q(accession_number__icontains=query) | Q(call_number__icontains=query)).values('id')
        )
        borrower_q = Q(borrower__first_name__icontains=query) | Q(borrower__last_name__icontains=query) | Q(borrower__email__icontains=query)

        borrowed_records = borrowed_records.filter(book_q | periodical_q | borrower_q)

        for record in borrowed_records:
            if record.publication:
                record.highlighted_title = mark_safe(
                    record.publication.title.replace(query, f'<span class="bg-yellow-200">{query}</span>')
                )

    return render(request, 'library/partials/_borrowed_books_table.html', {'borrowed_records': borrowed_records, 'query': query})

@staff_member_required
def get_overdue_books_table(request):
    overdue_records = BorrowRecord.objects.filter(status='overdue').select_related('borrower').prefetch_related('publication').order_by('-due_date')
    return render(request, 'library/partials/_overdue_books_table.html', {'overdue_records': overdue_records})

@staff_member_required
def get_dashboard_content(request):
    all_books = Book.objects.all().order_by('-created_at')[:5]
    overdue_records = BorrowRecord.objects.filter(status='overdue').select_related('borrower').prefetch_related('publication').order_by('-due_date')[:5]
    returned_records = BorrowRecord.objects.filter(status='returned').select_related('borrower').prefetch_related('publication').order_by('-return_date')[:5]
    context = {
        'all_books': all_books,
        'overdue_records': overdue_records,
        'returned_records': returned_records,
    }
    return render(request, 'library/partials/_dashboard_content.html', context)

@staff_member_required
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f'Successfully updated "{book.title}".')
            return redirect('library:librarian_dashboard')
    else:
        form = BookForm(instance=book)
    
    return render(request, 'library/edit_book.html', {'form': form, 'book': book})

@staff_member_required
def delete_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        book.delete()
        messages.success(request, f'Successfully deleted "{book.title}".')
        return redirect('library:librarian_dashboard')
    
    return render(request, 'library/delete_book_confirm.html', {'book': book})

@staff_member_required
def borrow_record_detail(request, record_id):
    record = get_object_or_404(BorrowRecord.objects.select_related('publication', 'borrower'), id=record_id)
    return render(request, 'library/borrow_record_detail.html', {'record': record})

@staff_member_required
def send_reminder(request, record_id):
    record = get_object_or_404(BorrowRecord, id=record_id)
    if record.status == 'overdue':
        LibraryEmailService.send_overdue_notice(record)
        messages.success(request, f'Overdue notice sent to {record.borrower.email}.')
    elif record.days_until_due and record.days_until_due <= 3:
        LibraryEmailService.send_first_reminder(record)
        messages.success(request, f'Reminder sent to {record.borrower.email}.')
    else:
        messages.warning(request, 'No reminder needed for this record yet.')
    
    return redirect('library:librarian_dashboard')

@staff_member_required
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'Successfully added "{book.title}".')
            return redirect('library:librarian_dashboard')
    else:
        form = BookForm()
    
    return render(request, 'library/add_book.html', {'form': form})

@staff_member_required
def generate_report(request, report_type):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y-%m-%d")}.csv"'

    writer = csv.writer(response)

    if report_type == 'borrowed':
        writer.writerow(['Publication Title', 'Borrower', 'Borrow Date', 'Due Date', 'Status'])
        records = BorrowRecord.objects.filter(status__in=['active', 'overdue']).select_related('publication', 'borrower')
        for record in records:
            writer.writerow([record.publication.title, record.borrower.get_full_name(), record.borrow_date.strftime('%Y-%m-%d'), record.due_date.strftime('%Y-%m-%d'), record.get_status_display()])
    elif report_type == 'overdue':
        writer.writerow(['Publication Title', 'Borrower', 'Due Date', 'Fine'])
        records = BorrowRecord.objects.filter(status='overdue').select_related('publication', 'borrower')
        for record in records:
            writer.writerow([record.publication.title, record.borrower.get_full_name(), record.due_date.strftime('%Y-%m-%d'), record.fine_amount])
    else:
        return HttpResponse("Invalid report type.", status=400)

    return response

@staff_member_required
def dashboard_renew_book(request, record_id):
    record = get_object_or_404(BorrowRecord, id=record_id)
    if request.method == 'POST':
        try:
            record.renew()
            messages.success(request, f'Publication "{record.publication.title}" renewed for {record.borrower.get_full_name()}.')
        except ValueError as e:
            messages.error(request, str(e))
        
        # Create a response that triggers a full page refresh
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response

    return render(request, 'library/dashboard_renew_book_confirm.html', {'record': record})

@staff_member_required
def dashboard_return_book(request, record_id):
    record = get_object_or_404(BorrowRecord, id=record_id)
    if request.method == 'POST':
        record.return_book()
        messages.success(request, f'Publication "{record.publication.title}" returned by {record.borrower.get_full_name()}.')
        
        # Create a response that triggers a full page refresh
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response

    return render(request, 'library/dashboard_return_book_confirm.html', {'record': record})

@staff_member_required
def dashboard_mark_as_paid(request, record_id):
    record = get_object_or_404(BorrowRecord, id=record_id)
    if request.method == 'POST':
        record.fine_paid = True
        record.save()
        messages.success(request, f'Fine for "{record.publication.title}" marked as paid for {record.borrower.get_full_name()}.')
        
        # Create a response that triggers a full page refresh
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response

    return render(request, 'library/dashboard_mark_as_paid_confirm.html', {'record': record})

@staff_member_required
def get_returned_books_table(request):
    returned_records = BorrowRecord.objects.filter(status='returned').select_related('borrower').prefetch_related('publication').order_by('-return_date')
    return render(request, 'library/partials/_returned_books_table.html', {'returned_records': returned_records})

@staff_member_required
def download_returned_books_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="returned_books_report_{timezone.now().strftime("%Y-%m-%d")}.csv'

    writer = csv.writer(response)
    writer.writerow(['Publication Title', 'Borrower', 'Return Date', 'Fine'])

    records = BorrowRecord.objects.filter(status='returned').select_related('borrower').prefetch_related('publication')
    for record in records:
        publication_title = record.publication.title if record.publication else "[Deleted Publication]"
        writer.writerow([publication_title, record.borrower.get_full_name(), record.return_date.strftime('%Y-%m-%d'), record.fine_amount])

    return response