"""
Utility functions for the LMS application
"""

from django.db.models import Count, Q
from .models import (
    Course, CourseModule, CourseContent, ContentAccess, ModuleProgress,
    Quiz, QuizTaker, StudentCertificate, CertificateTemplate
)


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
    
    module_states = get_module_progress_states(course, student)
    total_modules = len(module_states)
    completed_modules = len([state for state in module_states if state['completed']])
    module_percentage = (completed_modules / total_modules) * 100 if total_modules else 0

    return {
        'percentage': round(percentage, 1),
        'completed_count': completed_contents,
        'total_count': total_count,
        'module_percentage': round(module_percentage, 1),
        'completed_modules': completed_modules,
        'total_modules': total_modules,
        'course_completed': total_modules > 0 and completed_modules == total_modules,
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


def get_previous_module(module):
    return CourseModule.objects.filter(
        course=module.course,
        order__lt=module.order
    ).order_by('-order', '-id').first()


def get_module_assessment(module):
    if getattr(module, 'skip_assessment', False):
        return None
    return Quiz.objects.filter(module=module, draft=False).order_by('id').first()


def is_first_module(module):
    return get_previous_module(module) is None


def is_module_unlocked(module, student):
    if not student:
        return False

    previous_module = get_previous_module(module)
    if previous_module is None:
        return True

    return ModuleProgress.objects.filter(
        student=student,
        module=previous_module,
        content_completed=True,
        assessment_passed=True,
    ).exists()


def update_module_content_completion(module, student):
    progress, _ = ModuleProgress.objects.get_or_create(student=student, module=module)
    total_contents = module.contents.count()
    completed_contents = ContentAccess.objects.filter(
        student=student,
        content__module=module,
        completed=True,
    ).count()
    progress.content_completed = total_contents == 0 or completed_contents >= total_contents
    if getattr(module, 'skip_assessment', False):
        progress.assessment_passed = True
    progress.refresh_completion()
    return progress


def update_module_assessment_completion(quiz_taker):
    module = quiz_taker.quiz.module
    if not module:
        return None

    progress, _ = ModuleProgress.objects.get_or_create(
        student=quiz_taker.user,
        module=module,
    )

    if quiz_taker.score > progress.best_score:
        progress.best_score = quiz_taker.score
        progress.best_quiz_taker = quiz_taker

    if quiz_taker.score >= ModuleProgress.PASSING_PERCENTAGE:
        progress.assessment_passed = True

    progress.refresh_completion()
    return progress


def get_module_progress_states(course, student):
    modules = list(course.modules.prefetch_related('contents', 'quizzes').all())
    progress_map = {
        item.module_id: item
        for item in ModuleProgress.objects.filter(student=student, module__course=course)
    } if student else {}
    states = []
    previous_completed = True

    for index, module in enumerate(modules):
        progress = progress_map.get(module.id)
        unlocked = index == 0 or previous_completed
        assessment = get_module_assessment(module)
        completed = bool(progress and progress.completed)
        states.append({
            'module': module,
            'progress': progress,
            'unlocked': unlocked,
            'completed': completed,
            'assessment': assessment,
            'skip_assessment': getattr(module, 'skip_assessment', False),
            'content_completed': bool(progress and progress.content_completed),
            'assessment_passed': bool(progress and progress.assessment_passed),
            'best_score': progress.best_score if progress else 0,
        })
        previous_completed = completed

    return states


def is_course_completed(course, student):
    states = get_module_progress_states(course, student)
    return bool(states) and all(state['completed'] for state in states)


def issue_certificate_if_eligible(course, student_profile):
    if not student_profile or not is_course_completed(course, student_profile):
        return None

    template = CertificateTemplate.objects.filter(course=course, status='active').first()
    if not template:
        template = CertificateTemplate.objects.filter(course=course).order_by('-updated_at').first()

    if not template:
        template = CertificateTemplate.objects.create(
            course=course,
            title='Certificate of Completion',
            organization_name='ChuoSmart Academy',
            instructor_name=', '.join(
                instructor.user.get_full_name() or instructor.user.username
                for instructor in course.instructors.all()[:2]
            ),
            status='active',
        )

    certificate, _ = StudentCertificate.objects.get_or_create(
        student=student_profile.user,
        course=course,
        defaults={'template': template},
    )

    if not certificate.template_id and template:
        certificate.template = template
        certificate.save(update_fields=['template'])

    return certificate
