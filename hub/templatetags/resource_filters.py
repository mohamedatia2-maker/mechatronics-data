from django import template
from hub.utils import get_subject_icon

register = template.Library()

@register.filter
def count_by_category(resources, category):
    """Count resources that match the given category"""
    return resources.filter(category=category).count()

@register.filter
def filename(value):
    """Get the basename of a path"""
    import os
    return os.path.basename(value)

@register.filter
def subject_icon(subject_name):
    """Returns a FontAwesome icon class string based on keywords in the subject name"""
    return get_subject_icon(subject_name)

@register.filter
def is_pdf(value):
    """Returns True if the URL points to a PDF or a Google Drive file"""
    if not value:
        return False
    v = str(value).lower()
    return '.pdf' in v or 'drive.google.com' in v
