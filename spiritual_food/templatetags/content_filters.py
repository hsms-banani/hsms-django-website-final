import html
from django import template

register = template.Library()

@register.filter(name='force_unescape')
def force_unescape(value):
    """
    Forces HTML un-escaping of a string.
    """
    return html.unescape(value)
