# core/templatetags/cart_extras.py

from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """
    Multiplies the value by argument.
    Usage: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """
    Subtracts argument from value.
    Usage: {{ value|subtract:arg }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def after_discount(price, discount):
    """
    Returns price after discount: price * (1 - discount)
    Usage: {{ product.price|after_discount:product.discount }}
    """
    try:
        return float(price) * (1 - float(discount)/100)
    except (ValueError, TypeError):
        return price


@register.filter
def get_item(dictionary, key):
    """
    Usage: {{ cart|get_item:product.id }}
    Gets the value from dictionary using key (e.g. cart['1'])
    """
    return dictionary.get(str(key))  # Convert key to string (session keys are strings)


@register.filter
def as_percent(value):
    """
    Converts decimal to percentage (e.g., 0.2 → 20%)
    Usage: {{ discount|as_percent }}
    """
    try:
        return f"{float(value):.0f}%"
    except (ValueError, TypeError):
        return "0%"


@register.filter
def dict_values_sum(dictionary):
    """
    Returns the sum of all values in a dictionary.
    For cart: {'1': 2, '3': 1} → 3
    """
    try:
        return sum(int(v) for v in dictionary.values())
    except:
        return 0