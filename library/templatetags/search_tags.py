# library/templatetags/search_tags.py

from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def highlight(text, query):
    """Highlight search terms in text"""
    if not query or not text:
        return text
    
    # Handle multiple words in query
    query_words = query.split()
    highlighted_text = str(text)
    
    for word in query_words:
        if len(word) >= 2:  # Only highlight words with 2+ characters
            # Use word boundaries to avoid partial matches within words
            pattern = r'\b(' + re.escape(word) + r')\b'
            highlighted_text = re.sub(
                pattern, 
                r'<span class="search-highlight">\1</span>', 
                highlighted_text, 
                flags=re.IGNORECASE
            )
    
    return mark_safe(highlighted_text)

@register.simple_tag
def search_score(book, query):
    """Calculate and return search relevance score for display"""
    if not query:
        return 0
    
    score = 0
    query_lower = query.lower()
    
    # Title match
    if query_lower in book.title.lower():
        score += 50
    
    # Author match
    if query_lower in book.authors_list.lower():
        score += 30
    
    # Category match
    if query_lower in book.category.name.lower():
        score += 20
    
    # Keywords match
    if book.keywords and query_lower in book.keywords.lower():
        score += 15
    
    return min(score, 100)  # Cap at 100

@register.filter
def truncate_smart(text, length=150):
    """Smart truncation that tries to break at word boundaries"""
    if len(text) <= length:
        return text
    
    truncated = text[:length]
    last_space = truncated.rfind(' ')
    
    if last_space > length * 0.8:  # If we can break at a reasonable point
        return truncated[:last_space] + '...'
    
    return truncated + '...'