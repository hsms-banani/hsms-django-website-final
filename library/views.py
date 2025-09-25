# library/views.py

from django.shortcuts import render, get_object_or_404
from django.db import connections
from django.http import JsonResponse
from django.db.models import Q, Count, Case, When, Prefetch

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
from .models import Book, Category, Author, Publisher, BookSearch
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.contrib import messages

import csv
from django.http import HttpResponse

# Cache timeouts
CACHE_TIMEOUT_SHORT = 60 * 5   # 5 minutes
CACHE_TIMEOUT_MEDIUM = 60 * 15  # 15 minutes
CACHE_TIMEOUT_LONG = 60 * 60    # 1 hour

def get_optimized_book_queryset():
    """Get optimized book queryset with all relations prefetched"""
    return Book.objects.select_related(
        'publisher', 
        'category'
    ).prefetch_related(
        Prefetch('authors', queryset=Author.objects.only('id', 'first_name', 'last_name', 'slug'))
    ).only(
        'id', 'title', 'subtitle', 'slug', 'publication_year', 
        'isbn_10', 'isbn_13', 'call_number', 'keywords', 
        'status', 'copies_available', 'total_copies', 'times_borrowed',
        'created_at', 'cover_image', 'classification_number', 'cutter_number',
        'publisher__name', 'publisher__slug',
        'category__name', 'category__slug'
    )

def download_csv_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="book_import_template.csv"'

    writer = csv.writer(response)
    header = [
        'title*', 'subtitle', 'author*', 'publisher*', 'publication_year*', 
        'isbn_10', 'isbn_13', 'classification_number*', 'cutter_number*', 
        'category*', 'language', 'pages', 'edition', 'description', 
        'keywords', 'total_copies', 'copies_available', 'location_shelf', 'status'
    ]
    writer.writerow(header)
    writer.writerow([
        'Sample Book Title', 'A Sample Subtitle', 'Author One;Author Two', 'Sample Publisher', '2023',
        '1234567890', '9781234567890', '230.1', 'S64i', 'Systematic Theology', 'en', '450', '3rd Edition',
        'A sample book description.', 'theology,christianity,doctrine', '3', '2', 'A-1-5', 'available'
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
            
            try:
                call_command('import_books', file_path)
                messages.success(request, f'Successfully imported books from {filename}.')
            except Exception as e:
                messages.error(request, f'Error importing books: {e}')
            
            return render(request, 'library/upload_csv.html')
        else:
            messages.error(request, 'No CSV file selected.')

    return render(request, 'library/upload_csv.html')


def _get_filtered_sorted_books(request):
    """
    Applies search, filtering, and sorting to the main book queryset based on request GET parameters.
    Returns a fully filtered and sorted queryset.
    """
    books = get_optimized_book_queryset()
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', '-created_at')
    using_postgres = connections['default'].vendor == 'postgresql'

    # --- Search ---
    if query:
        if using_postgres:
            search_vector = (
                SearchVector('title', weight='A') + 
                SearchVector('subtitle', weight='B') +
                SearchVector('authors__first_name', weight='B') +
                SearchVector('authors__last_name', weight='B') + 
                SearchVector('isbn_10', weight='C') +
                SearchVector('isbn_13', weight='C') +
                SearchVector('keywords', weight='C') +
                SearchVector('call_number', weight='D')
            )
            search_query = SearchQuery(query)
            books = books.annotate(
                rank=SearchRank(search_vector, search_query)
            ).filter(rank__gte=0.1)
        else:
            query_words = query.split()
            final_q = Q()
            for word in query_words:
                word_q = (
                    Q(title__icontains=word) | Q(subtitle__icontains=word) |
                    Q(authors__first_name__icontains=word) | Q(authors__last_name__icontains=word) |
                    Q(isbn_10__icontains=word) | Q(isbn_13__icontains=word) |
                    Q(keywords__icontains=word) | Q(call_number__icontains=word) |
                    Q(publisher__name__icontains=word) | Q(category__name__icontains=word)
                )
                final_q &= word_q
            if final_q:
                books = books.filter(final_q).distinct()
            else:
                books = books.none()

        try:
            search_obj, created = BookSearch.objects.get_or_create(query=query)
            if not created:
                search_obj.search_count += 1
                search_obj.save(update_fields=['search_count', 'last_searched'])
        except:
            pass

    # --- Filtering ---
    category_slug = request.GET.get('category')
    if category_slug:
        books = books.filter(category__slug=category_slug)

    author_slug = request.GET.get('author')
    author_q = request.GET.get('author_q')
    if author_slug:
        books = books.filter(authors__slug=author_slug)
    elif author_q:
        books = books.filter(Q(authors__first_name__icontains=author_q) | Q(authors__last_name__icontains=author_q)).distinct()

    publisher_slug = request.GET.get('publisher')
    publisher_q = request.GET.get('publisher_q')
    if publisher_slug:
        books = books.filter(publisher__slug=publisher_slug)
    elif publisher_q:
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
        'call_number', '-call_number'
    ]
    if query and using_postgres:
        valid_sorts.append('relevance')
        if sort_by == '-created_at': # Default sort for a search should be relevance
            sort_by = 'relevance'

    if sort_by == 'relevance' and 'rank' in books.query.annotations:
        books = books.order_by('-rank')
    elif sort_by in valid_sorts:
        books = books.order_by(sort_by)
    
    return books


def library_home(request):
    """Display a comprehensive, filterable list of books - OPTIMIZED"""
    books = _get_filtered_sorted_books(request)

    paginator = Paginator(books, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    filter_options = cache.get('library_filter_options_v2')
    if not filter_options:
        filter_options = {
            'categories': Category.objects.annotate(book_count=Count('books')).filter(book_count__gt=0).only('id', 'name', 'slug').order_by('name'),
        }
        cache.set('library_filter_options_v2', filter_options, CACHE_TIMEOUT_LONG)

    # Handle search box state after form submission
    author_q_value = request.GET.get('author_q', '')
    if request.GET.get('author') and not author_q_value:
        try:
            author_q_value = Author.objects.get(slug=request.GET.get('author')).full_name
        except Author.DoesNotExist:
            pass

    publisher_q_value = request.GET.get('publisher_q', '')
    if request.GET.get('publisher') and not publisher_q_value:
        try:
            publisher_q_value = Publisher.objects.get(slug=request.GET.get('publisher')).name
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
        },
        'search_query': request.GET.get('q', '').strip(),
        'sort_by': request.GET.get('sort', '-created_at'),
        'author_q_value': author_q_value,
        'publisher_q_value': publisher_q_value,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'library/partials/book_grid.html', context)

    return render(request, 'library/home.html', context)


def book_detail(request, slug):
    """Display detailed view of a single book - OPTIMIZED"""
    cache_key = f"book_detail_{slug}"
    context = cache.get(cache_key)
    
    if context is None:
        book = get_object_or_404(
            Book.objects.select_related('publisher', 'category')
                       .prefetch_related('authors'), 
            slug=slug
        )
        
        related_books = Book.objects.filter(
            Q(category=book.category) | Q(authors__in=book.authors.all())
        ).exclude(id=book.id).distinct().select_related(
            'publisher', 'category'
        ).prefetch_related('authors').only(
            'id', 'title', 'slug', 'call_number', 'status', 
            'copies_available', 'total_copies', 'cover_image',
            'publisher__name', 'category__name'
        )[:6]
        
        context = {
            'book': book,
            'related_books': list(related_books),
        }
        
        cache.set(cache_key, context, CACHE_TIMEOUT_MEDIUM)
    
    return render(request, 'library/book_detail.html', context)


@require_http_methods(["GET"])
def quick_search(request):
    """HTMX quick search for autocomplete - OPTIMIZED"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return render(request, 'library/partials/quick_search_results.html', 
                     {'results': [], 'query': query})
    
    cache_key = f"quick_search_{hash(query)}"
    results = cache.get(cache_key)
    
    if results is None:
        books = Book.objects.select_related('publisher', 'category').prefetch_related(
            'authors'
        ).only(
            'id', 'title', 'slug', 'isbn_10', 'isbn_13', 'call_number',
            'status', 'copies_available', 'total_copies',
            'publisher__name', 'category__name'
        )
        
        db_results = optimized_database_search(books, query)
        
        results = [book for book, score in db_results[:10]]
        
        cache.set(cache_key, results, 120)
    
    return render(request, 'library/partials/quick_search_results.html', {
        'results': results, 
        'query': query
    })

def optimized_database_search(books, query):
    """Optimized database search with scoring for autocomplete"""
    using_postgres = connections['default'].vendor == 'postgresql'
    
    if using_postgres:
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
        ).filter(rank__gte=0.1).order_by('-rank')
        
        return [(book, float(book.rank) * 100) for book in books_with_rank[:15]]
    else:
        # SQLite fallback with basic scoring
        query_words = query.lower().split()
        scored_books = []
        
        q_objects = []
        for word in query_words:
            if len(word) >= 2:
                q_objects.append(
                    Q(title__icontains=word) |
                    Q(authors__first_name__icontains=word) |
                    Q(authors__last_name__icontains=word) |
                    Q(isbn_10__icontains=word) |
                    Q(isbn_13__icontains=word) |
                    Q(call_number__icontains=word)
                )
        
        if q_objects:
            filtered_books = books.filter(reduce(operator.or_, q_objects)).distinct()
            
            for book in filtered_books[:20]:
                score = 0
                title_lower = book.title.lower()
                if query.lower() in title_lower:
                    score += 100
                for word in query_words:
                    if word in title_lower:
                        score += 30
                if score > 0:
                    scored_books.append((book, score))
        
        return sorted(scored_books, key=lambda x: x[1], reverse=True)

@cache_page(CACHE_TIMEOUT_LONG)
def category_list(request):
    """Display all categories - CACHED"""
    categories = Category.objects.annotate(
        book_count=Count('books')
    ).only('id', 'name', 'slug', 'description').order_by('name')
    
    return render(request, 'library/category_list.html', {
        'categories': categories
    })

def category_books(request, slug):
    """Display books in a specific category - OPTIMIZED"""
    category = get_object_or_404(Category.objects.only('id', 'name', 'slug'), slug=slug)
    
    books = get_optimized_book_queryset().filter(category=category)
    
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/category_books.html', {
        'category': category,
        'page_obj': page_obj
    })

@cache_page(CACHE_TIMEOUT_LONG)
def author_list(request):
    """Display all authors - CACHED"""
    authors = Author.objects.annotate(
        book_count=Count('books')
    ).only('id', 'first_name', 'last_name', 'slug', 'bio').order_by('last_name', 'first_name')
    
    paginator = Paginator(authors, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/author_list.html', {
        'page_obj': page_obj
    })

def author_detail(request, slug):
    """Display author details and their books - OPTIMIZED"""
    author = get_object_or_404(Author.objects.only('id', 'first_name', 'last_name', 'slug', 'bio'), slug=slug)
    
    books = get_optimized_book_queryset().filter(authors=author)
    
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/author_detail.html', {
        'author': author,
        'page_obj': page_obj
    })

def publisher_list(request):
    """Display all publishers"""
    publishers = cache.get('library_publisher_list')
    if not publishers:
        publishers = Publisher.objects.annotate(
            book_count=Count('books')
        ).order_by('name')
        cache.set('library_publisher_list', publishers, 60 * 15)

    paginator = Paginator(publishers, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'library/publisher_list.html', context)

def publisher_detail(request, slug):
    """Display publisher details and their books"""
    publisher = get_object_or_404(Publisher, slug=slug)
    books = Book.objects.filter(publisher=publisher).select_related('publisher', 'category').prefetch_related('authors')
    
    paginator = Paginator(books, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'publisher': publisher,
        'page_obj': page_obj,
    }
    return render(request, 'library/publisher_detail.html', context)

# HTMX Views for dynamic loading
@require_http_methods(["GET"])
def load_more_books(request):
    """Load more books for infinite scroll - OPTIMIZED"""
    books = _get_filtered_sorted_books(request)
    paginator = Paginator(books, 16) # Consistent pagination
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/partials/load_more_response.html', {'page_obj': page_obj})

def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return render(request, 'library/partials/search_suggestions.html', {'suggestions': []})

    query_words = query.split()

    q_objects = [Q(title__icontains=word) for word in query_words]

    if q_objects:
        books = Book.objects.filter(reduce(operator.and_, q_objects)).values_list('title', flat=True).distinct()[:10]
    else:
        books = []
    
    suggestions = list(books)
    
    return render(request, 'library/partials/search_suggestions.html', {'suggestions': suggestions})

def get_authors_for_category(request):
    category_slug = request.GET.get('category')
    authors = Author.objects.all()
    if category_slug:
        authors = authors.filter(books__category__slug=category_slug).distinct()
    
    return render(request, 'library/partials/author_options.html', {'authors': authors.order_by('last_name', 'first_name')})

def search_authors(request):
    query = request.GET.get('author_q', '').strip()
    authors = []
    if len(query) >= 2:
        authors = Author.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).annotate(book_count=Count('books')).order_by('-book_count')[:10]
    
    return render(request, 'library/partials/_author_search_results.html', {
        'authors': authors
    })

def search_publishers(request):
    query = request.GET.get('publisher_q', '').strip()
    publishers = []
    if len(query) >= 2:
        publishers = (
            Publisher.objects.filter(name__icontains=query)
            .annotate(book_count=Count('books'))
            .order_by('-book_count')[:10]
        )
    
    return render(request, 'library/partials/_publisher_search_results.html', {
        'publishers': publishers
    })