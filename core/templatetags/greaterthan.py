# https://stackoverflow.com/a/1427964
from django import template

register = template.Library()


@register.filter
def gt(a, b):
    return a > b
