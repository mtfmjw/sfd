from django import template

register = template.Library()


@register.filter
def get_attr(obj, name):
    """Template filter to get an attribute of an object dynamically."""
    try:
        return getattr(obj, name)
    except (AttributeError, TypeError):
        return None
