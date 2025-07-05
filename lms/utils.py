"""
Utility functions for the LMS application
"""

from django.db.models import Count, Q
from .models import Course, CourseContent, ContentAccess


def calculate_course_progress(course, student):
    """
    Calculate a student's progress in a course
    
    Args:
        course: Course object
        student: LMSProfile object
    
    Returns:
        dict with:
            - percentage: float - percentage of content completed
            - completed_count: int - number of content items completed
            - total_count: int - total number of content items
    """
    # Get all content items for the course
    course_contents = CourseContent.objects.filter(module__course=course)
    total_count = course_contents.count()
    
    if total_count == 0:
        return {
            'percentage': 0,
            'completed_count': 0,
            'total_count': 0
        }
    
    # Get completed content items
    completed_contents = ContentAccess.objects.filter(
        student=student,
        content__module__course=course,
        completed=True
    ).count()
    
    # Calculate percentage
    percentage = (completed_contents / total_count) * 100 if total_count > 0 else 0
    
    return {
        'percentage': round(percentage, 1),
        'completed_count': completed_contents,
        'total_count': total_count
    }


def get_all_enrolled_students_progress(course):
    """
    Get progress data for all students enrolled in a course
    
    Args:
        course: Course object
    
    Returns:
        dict mapping student_id to progress data
    """
    progress_data = {}
    
    # Get all enrolled students
    for enrollment in course.courseenrollment_set.all():
        student = enrollment.student
        progress = calculate_course_progress(course, student)
        progress_data[student.id] = {
            'student': student,
            'progress': progress
        }
    
    return progress_data
