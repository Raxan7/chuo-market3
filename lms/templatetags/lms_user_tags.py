"""
Template tags for LMS user roles and permissions
"""

from django import template
from django.template.defaultfilters import stringfilter
from ..views import is_instructor, is_student, is_admin, is_course_instructor

register = template.Library()

@register.filter(name='is_instructor')
def is_instructor_filter(user):
    """
    Template filter to check if a user is an instructor
    """
    return is_instructor(user)

@register.filter(name='is_student')
def is_student_filter(user):
    """
    Template filter to check if a user is a student
    """
    return is_student(user)

@register.filter(name='is_admin')
def is_admin_filter(user):
    """
    Template filter to check if a user is an admin
    """
    if not user.is_authenticated:
        return False
        
    try:
        return hasattr(user, 'lms_profile') and user.lms_profile.role == 'admin'
    except Exception:
        return False

@register.filter(name='is_course_instructor')
def is_course_instructor_filter(user, course):
    """
    Template filter to check if a user is an instructor for a specific course
    """
    if not user.is_authenticated:
        return False
    
    if not hasattr(user, 'lms_profile'):
        return False
        
    try:
        # Check if user is admin or course instructor
        return is_admin_filter(user) or course.instructors.filter(id=user.lms_profile.id).exists()
    except Exception:
        return False
