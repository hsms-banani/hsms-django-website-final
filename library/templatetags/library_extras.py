# library/templatetags/library_extras.py

from django import template

register = template.Library()

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