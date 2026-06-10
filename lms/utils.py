"""
Utility functions for the LMS application
"""

import logging

from django.db.models import Count, Q
from .models import (
    Course, CourseModule, CourseContent, ContentAccess, ModuleProgress,
    Quiz, QuizTaker, StudentCertificate, CertificateTemplate, ActivityLog
)

logger = logging.getLogger(__name__)


def _log_learning_record_event(message):
    logger.info(message)
    try:
        ActivityLog.objects.create(message=message)
    except Exception:
        logger.exception("Could not write LMS learning record activity log: %s", message)


def calculate_course_progress(course, student):
    """
    Calculate a student's progress in a course.

    The first module (intro/overview) is always open and never counts
    toward the progress bar or course-completion gate.

    Progress is now quiz-completion-based: a module is "complete" only when
    the student passes its assessment at or above the pass mark. The
    content-view-based numbers are still returned for backward compatibility
    but ``percentage`` and ``module_percentage`` both reflect the same
    quiz-completion metric so dashboards show consistent data.

    Args:
        course: Course object
        student: LMSProfile object

    Returns:
        dict with:
            - percentage: float - quiz-completion based progress (0-100)
            - completed_count: int - number of modules with quiz passed
            - total_count: int - total number of modules
            - completed_contents: int - number of content items completed
            - total_contents: int - total number of content items
            - module_percentage: float - same as ``percentage`` (kept for back-compat)
            - completed_modules: int - same as ``completed_count``
            - total_modules: int - same as ``total_count``
            - course_completed: bool - all modules have quiz passed
            - last_activity: datetime - last quiz attempt or content access
    """
    module_states = get_module_progress_states(course, student)
    countable = [s for s in module_states if not s['is_first_module']]
    total_modules = len(countable)
    completed_modules = len([s for s in countable if s['completed']])
    if total_modules == 0:
        module_percentage = 100.0
    else:
        module_percentage = (completed_modules / total_modules) * 100

    course_contents = CourseContent.objects.filter(module__course=course)
    total_contents = course_contents.count()
    completed_contents = ContentAccess.objects.filter(
        student=student,
        content__module__course=course,
        completed=True,
    ).count() if student else 0

    last_quiz_at = None
    last_content_at = None
    if student:
        last_quiz = (
            QuizTaker.objects
            .filter(user=student, quiz__module__course=course, completed=True)
            .order_by('-date_completed')
            .values_list('date_completed', flat=True)
            .first()
        )
        last_content_at = (
            ContentAccess.objects
            .filter(student=student, content__module__course=course)
            .order_by('-accessed_at')
            .values_list('accessed_at', flat=True)
            .first()
        )
        last_quiz_at = last_quiz

    candidates = [t for t in (last_quiz_at, last_content_at) if t is not None]
    last_activity = max(candidates) if candidates else None

    return {
        'percentage': round(module_percentage, 1),
        'completed_count': completed_modules,
        'total_count': total_modules,
        'completed_contents': completed_contents,
        'total_contents': total_contents,
        'module_percentage': round(module_percentage, 1),
        'completed_modules': completed_modules,
        'total_modules': total_modules,
        'course_completed': (total_modules > 0 and completed_modules == total_modules) or (total_modules == 0 and len(module_states) > 0),
        'last_activity': last_activity,
    }


def get_all_enrolled_students_progress(course):
    """
    Get progress data for all students enrolled in a course.

    Each entry also carries per-student best quiz score and a flag for
    whether the student has passed at least one module, so instructor
    dashboards can show accurate quiz-completion based progress.

    Args:
        course: Course object

    Returns:
        dict mapping student_id to progress data
    """
    progress_data = {}

    enrollments = list(course.courseenrollment_set.select_related('student__user'))
    student_ids = [e.student_id for e in enrollments]
    module_ids = list(course.modules.values_list('id', flat=True))

    best_scores = {}
    if module_ids and student_ids:
        rows = (
            ModuleProgress.objects
            .filter(student_id__in=student_ids, module_id__in=module_ids)
            .values('student_id', 'best_score')
        )
        for row in rows:
            sid = row['student_id']
            current = best_scores.get(sid, 0)
            score = float(row['best_score'] or 0)
            if score > current:
                best_scores[sid] = score

    for enrollment in enrollments:
        student = enrollment.student
        progress = calculate_course_progress(course, student)
        progress_data[student.id] = {
            'student': student,
            'progress': progress,
            'best_score': best_scores.get(student.id, 0),
        }

    return progress_data


def get_previous_module(module):
    return module.get_previous_module()


def get_next_module(module):
    return module.get_next_module()


def get_module_assessment(module, student=None):
    if getattr(module, 'skip_assessment', False):
        return None

    if student:
        personal_quiz = Quiz.objects.filter(
            module=module,
            generated_for=student,
            draft=False,
        ).order_by('id').first()
        if personal_quiz:
            return personal_quiz

    return Quiz.objects.filter(
        module=module,
        generated_for__isnull=True,
        draft=False,
    ).order_by('id').first()


def ensure_course_learning_records(course, student, queue_assessments=True, force_assessment_regeneration=False):
    """
    Ensure an enrolled learner has module progress rows and AI quiz jobs.

    This is intentionally idempotent so it can run from enrollment signals,
    module/content changes, and course detail rendering without creating
    duplicate quizzes or progress records.
    """
    if not course or not student:
        return {
            'progress_created': 0,
            'progress_existing': 0,
            'assessments_queued': 0,
            'assessments_skipped': 0,
        }

    stats = {
        'progress_created': 0,
        'progress_existing': 0,
        'assessments_queued': 0,
        'assessments_skipped': 0,
    }

    for module in course.modules.order_by('order', 'id'):
        progress, created = ModuleProgress.objects.get_or_create(
            student=student,
            module=module,
        )
        if created:
            stats['progress_created'] += 1
            _log_learning_record_event(
                "Created module progress for student %s, course %s, module %s." % (
                    student.id,
                    course.id,
                    module.id,
                )
            )
        else:
            stats['progress_existing'] += 1

        content_completed_before = progress.content_completed
        progress = update_module_content_completion(module, student)
        if progress.content_completed != content_completed_before:
            _log_learning_record_event(
                "Updated content progress for student %s, course %s, module %s: content_completed=%s." % (
                    student.id,
                    course.id,
                    module.id,
                    progress.content_completed,
                )
            )

        if getattr(module, 'skip_assessment', False):
            stats['assessments_skipped'] += 1
            continue

        if queue_assessments:
            from .ai_assessments import queue_module_assessment_generation

            quiz = queue_module_assessment_generation(
                module,
                student=student,
                force=force_assessment_regeneration,
            )
            if quiz:
                stats['assessments_queued'] += 1

    _log_learning_record_event(
        "Ensured learning records for student %s in course %s: %s." % (
            student.id,
            course.id,
            stats,
        )
    )
    return stats


def is_first_module(module):
    return get_previous_module(module) is None


def module_unlocks_next(module, student):
    progress = ModuleProgress.objects.filter(student=student, module=module).first()
    if not progress:
        return False

    return progress.unlocks_next


def is_module_unlocked(module, student):
    if not student:
        return False

    return module.is_unlocked_for(student)


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
    pass_threshold = quiz_taker.quiz.pass_mark or ModuleProgress.PASSING_PERCENTAGE

    if quiz_taker.score > progress.best_score:
        progress.best_score = quiz_taker.score
        progress.best_quiz_taker = quiz_taker

    if quiz_taker.score >= pass_threshold:
        progress.assessment_passed = True
        # Automatically mark content as completed if the assessment is passed.
        # This ensures that passing the quiz immediately unlocks the next module,
        # even if some content items weren't explicitly marked as complete.
        progress.content_completed = True

    progress.refresh_completion()
    return progress


def get_module_progress_states(course, student):
    modules = list(course.modules.prefetch_related('contents', 'quizzes').order_by('order', 'id'))
    progress_map = {
        item.module_id: item
        for item in ModuleProgress.objects.filter(student=student, module__course=course)
    } if student else {}
    
    states = []
    previously_completed = True  # The first module is always unlocked
    
    for index, module in enumerate(modules):
        progress = progress_map.get(module.id)
        # Logic sequence gating: unlocked if the module BEFORE this one in the list was passed
        unlocked = previously_completed
        assessment = get_module_assessment(module, student=student)
        if not assessment:
            assessment_status = 'not_ready'
        elif assessment.generation_status in {'pending', 'processing'}:
            assessment_status = 'processing'
        elif assessment.generation_status == 'failed' and not assessment.questions.exists():
            assessment_status = 'failed'
        elif assessment.questions.exists():
            assessment_status = 'ready'
        else:
            assessment_status = 'not_ready'
        completed = bool(progress and progress.completed)
        states.append({
            'module': module,
            'progress': progress,
            'unlocked': unlocked,
            'completed': completed,
            'assessment': assessment,
            'assessment_status': assessment_status,
            'skip_assessment': getattr(module, 'skip_assessment', False),
            'content_completed': bool(progress and progress.content_completed),
            'assessment_passed': bool(progress and progress.assessment_passed),
            'best_score': progress.best_score if progress else 0,
            'previous_module': modules[index-1] if index > 0 else None,
            'lock_message': module.lock_message_for(student) if student else '',
            'is_first_module': index == 0,
        })
        
        # Update previously_completed for the next iteration in the sequence
        current_unlocked_next = bool(progress and progress.unlocks_next)
        previously_completed = current_unlocked_next

    return states


def is_course_completed(course, student):
    states = get_module_progress_states(course, student)
    if not states:
        return False
    countable = [s for s in states if not s['is_first_module']]
    if not countable:
        return True
    return all(s['completed'] for s in countable)


def instructors_missing_legal_name(course):
    """Return a list of instructor LMSProfiles that have not set a legal name."""
    return [i for i in course.instructors.all() if not i.has_legal_name]


def issue_certificate_if_eligible(course, student_profile):
    if not student_profile or not is_course_completed(course, student_profile):
        return None

    if not student_profile.has_legal_name:
        logger.info(
            "Skipping certificate for %s in %s: student has no legal name set.",
            student_profile.user.username, course.title,
        )
        return None

    if instructors_missing_legal_name(course):
        logger.info(
            "Skipping certificate for %s in %s: one or more instructors have no legal name.",
            student_profile.user.username, course.title,
        )
        return None

    template = CertificateTemplate.objects.filter(course=course, status='active').first()
    if not template:
        template = CertificateTemplate.objects.filter(course=course).order_by('-updated_at').first()

    if not template:
        instructor_names = ', '.join(
            instructor.display_legal_name or instructor.user.get_full_name() or instructor.user.username
            for instructor in course.instructors.all()[:2]
        ) or 'Course Instructor'
        template = CertificateTemplate.objects.create(
            course=course,
            title='Certificate of Completion',
            organization_name='ChuoSmart Academy',
            primary_color='#0d6efd',
            secondary_color='#111827',
            accent_color='#1FAA59',
            instructor_name=instructor_names,
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
