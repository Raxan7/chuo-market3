"""
Template tags for LMS user roles and permissions
"""

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='is_instructor')
def is_instructor_filter(user):
    """
    Template filter to check if a user is an instructor
    """
    if not user.is_authenticated:
        return False
        
    try:
        # First check if they have the instructor role directly
        if hasattr(user, 'lms_profile') and user.lms_profile.role == 'instructor':
            return True
            
        # If not, check if they have an approved instructor request
        has_approved_request = user.instructor_requests.filter(status='approved').exists()
        
        # If they have an approved request but role not updated,
        # update their role now (this should ideally be done elsewhere)
        if has_approved_request and hasattr(user, 'lms_profile') and user.lms_profile.role != 'instructor':
            user.lms_profile.role = 'instructor'
            user.lms_profile.save()
            return True
            
        return False
    except Exception:
        return False

@register.filter(name='is_student')
def is_student_filter(user):
    """
    Template filter to check if a user is a student
    """
    if not user.is_authenticated:
        return False
        
    try:
        return hasattr(user, 'lms_profile') and user.lms_profile.role == 'student'
    except Exception:
        return False

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
