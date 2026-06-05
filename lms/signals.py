"""
Signal handlers for the LMS application
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import transaction
from .models import LMSProfile, Course, CourseContent, CourseEnrollment, CourseModule
from .ai_assessments import queue_module_assessment_generation
from core.newsletter import send_course_newsletter, send_course_content_newsletter


def _enrollments_with_course_access(course):
    queryset = CourseEnrollment.objects.select_related('student', 'course').filter(course=course)
    if course.is_free:
        return queryset
    return queryset.filter(payment_status='approved')


@receiver(post_save, sender=User)
def create_lms_profile(sender, instance, created, **kwargs):
    """
    Create an LMS profile for a user
    """
    # Check if the user already has a profile
    if not hasattr(instance, 'lms_profile'):
        # For new users, set role to student by default
        # For existing users (admin users likely existed before LMS app), try to detect role
        role = 'student'
        if instance.is_staff and instance.is_superuser:
            role = 'admin'
        elif instance.is_staff:
            role = 'instructor'
        
        # Get phone number from Customer profile if available
        phone_number = None
        if hasattr(instance, 'customer') and instance.customer:
            phone_number = instance.customer.phone_number
            
        LMSProfile.objects.create(
            user=instance, 
            role=role,
            phone_number=phone_number
        )


@receiver(post_save, sender=Course)
def notify_new_course(sender, instance, created, **kwargs):
    if not created:
        return

    def dispatch_newsletter():
        related_courses = Course.objects.exclude(pk=instance.pk)
        if instance.program:
            related_courses = related_courses.filter(Q(program=instance.program) | Q(level=instance.level) | Q(course_type=instance.course_type))
        else:
            related_courses = related_courses.filter(Q(level=instance.level) | Q(course_type=instance.course_type))

        related_courses = related_courses.order_by('-id')[:3]
        send_course_newsletter(instance, related_courses)

    transaction.on_commit(dispatch_newsletter)


@receiver(post_save, sender=CourseContent)
def notify_new_course_content(sender, instance, created, **kwargs):
    def dispatch_newsletter():
        if not created:
            return
        related_contents = CourseContent.objects.filter(
            module__course=instance.module.course
        ).exclude(pk=instance.pk).order_by('-date_added')[:3]
        send_course_content_newsletter(instance, related_contents)

    transaction.on_commit(dispatch_newsletter)

    def dispatch_assessment_regeneration():
        from .utils import update_module_content_completion

        enrollments = list(_enrollments_with_course_access(instance.module.course))
        for enrollment in enrollments:
            update_module_content_completion(instance.module, enrollment.student)

        if getattr(instance.module, 'skip_assessment', False):
            return

        for enrollment in enrollments:
            queue_module_assessment_generation(
                instance.module,
                student=enrollment.student,
                force=True,
            )

    transaction.on_commit(dispatch_assessment_regeneration)


@receiver(post_save, sender=CourseModule)
def ensure_learning_records_on_module_save(sender, instance, created, **kwargs):
    """Create progress rows and AI quizzes when modules are added after enrollment."""
    def dispatch_learning_records():
        from .utils import ensure_course_learning_records

        for enrollment in _enrollments_with_course_access(instance.course):
            ensure_course_learning_records(
                instance.course,
                enrollment.student,
                queue_assessments=True,
                force_assessment_regeneration=False,
            )

    transaction.on_commit(dispatch_learning_records)


@receiver(post_save, sender=CourseEnrollment)
def queue_assessment_generation_on_enrollment(sender, instance, created, **kwargs):
    """Prepare personalized module assessments as soon as access is granted."""
    if not instance.course:
        return

    should_queue = instance.course.is_free or instance.payment_status in {'not_required', 'approved'}
    if not should_queue:
        return

    def dispatch_generation():
        from .utils import ensure_course_learning_records

        ensure_course_learning_records(
            instance.course,
            instance.student,
            queue_assessments=True,
            force_assessment_regeneration=False,
        )

    transaction.on_commit(dispatch_generation)
