# library/templatetags/library_filters.py
"""
Custom template filters for the library app
"""

from django import template

register = template.Library()

@register.filter
def abs_value(value):
    """Return the absolute value of a number"""
    try:
        return abs(value)
    except (ValueError, TypeError):
        return value

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def get_display_name(obj, language='en'):
    """Get display name based on language preference"""
    if hasattr(obj, 'get_display_name'):
        return obj.get_display_name(language)
    return str(obj)

@register.filter
def format_call_number(book):
    """Format the complete call number with volume"""
    if hasattr(book, 'full_call_number'):
        return book.full_call_number
    return book.call_number if hasattr(book, 'call_number') else ''

@register.filter
def format_authors(book, max_authors=3):
    """Format author names for display"""
    if not hasattr(book, 'authors'):
        return ''
    
    authors = book.authors.all()[:max_authors]
    author_names = []
    
    for author in authors:
        if author.full_name_bangla:
            author_names.append(author.full_name_bangla)
        else:
            author_names.append(author.full_name)
    
    if book.authors.count() > max_authors:
        return ', '.join(author_names) + ', et al.'
    
    return ', '.join(author_names)

@register.filter
def days_overdue_text(days):
    """Convert days overdue to readable text"""
    try:
        days = int(days)
        if days < 0:
            return f"{abs(days)} days overdue"
        elif days == 0:
            return "Due today!"
        elif days == 1:
            return "Due tomorrow"
        else:
            return f"{days} days left"
    except (ValueError, TypeError):
        return ""

@register.filter
def availability_badge_class(status):
    """Return CSS classes for availability badge"""
    status_classes = {
        'available': 'bg-green-100 text-green-800',
        'checked_out': 'bg-red-100 text-red-800',
        'reserved': 'bg-yellow-100 text-yellow-800',
        'lost': 'bg-gray-100 text-gray-800',
        'damaged': 'bg-orange-100 text-orange-800',
        'repair': 'bg-blue-100 text-blue-800',
    }
    return status_classes.get(status, 'bg-gray-100 text-gray-800')

@register.filter
def borrow_status_badge_class(status):
    """Return CSS classes for borrow status badge"""
    status_classes = {
        'active': 'bg-blue-100 text-blue-800',
        'returned': 'bg-gray-100 text-gray-800',
        'overdue': 'bg-red-100 text-red-800',
        'lost': 'bg-orange-100 text-orange-800',
    }
    return status_classes.get(status, 'bg-gray-100 text-gray-800')