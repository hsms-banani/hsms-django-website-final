# library/context_processors.py
from .models import Book, Author, Category

def library_stats(request):
    return {
        'total_books': Book.objects.count(),
        'total_authors': Author.objects.count(),
        'total_categories': Category.objects.count(),
    }