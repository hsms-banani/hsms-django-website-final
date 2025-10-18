from django import template
import json

register = template.Library()

@register.filter(is_safe=True)
def jsonify(obj):
    return json.dumps(obj)
