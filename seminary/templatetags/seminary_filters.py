# templatetags/content_filters.py
from django import template
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def preview_content(value, word_count=50):
    """
    Strip HTML tags and return clean preview text for leadership messages
    """
    if not value:
        return ""
    
    # Strip all HTML tags
    clean_text = strip_tags(value)
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    # Truncate to specified word count
    truncator = Truncator(clean_text)
    return truncator.words(word_count)

@register.filter
def smart_preview(value, word_count=50):
    """
    Smart preview that preserves some formatting but removes paragraph tags
    """
    if not value:
        return ""
    
    # Remove paragraph tags but keep other formatting like bold, italic
    text = re.sub(r'</?p[^>]*>', ' ', value)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    # Truncate HTML content
    from django.utils.text import Truncator
    truncator = Truncator(text)
    return mark_safe(truncator.words(word_count, html=True))