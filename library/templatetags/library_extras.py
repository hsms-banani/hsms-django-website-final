# library/templatetags/library_extras.py

from django import template
from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit

register = template.Library()

@register.simple_tag
def update_query_param(path, key, value):
    """Updates or adds a query parameter to a given URL path."""
    scheme, netloc, path, query_string, fragment = urlsplit(path)
    query_params = parse_qs(query_string)
    query_params[key] = value
    new_query_string = urlencode(query_params, doseq=True)
    return urlunsplit((scheme, netloc, path, new_query_string, fragment))

@register.simple_tag
def query_transform(request, **kwargs):
    """Transform URL query parameters for active filter pills and pagination"""
    updated = request.GET.copy()
    for k, v in kwargs.items():
        if v is not None and v != '':
            updated[k] = v
        elif k in updated:
            del updated[k]
    return updated.urlencode()