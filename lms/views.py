"""
Views for the LMS application
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import (
    
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, TemplateView, View
)
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import time

from .models import (
    LMSProfile, Program, Course, CourseModule, CourseContent, Quiz, Question,
    MCQuestion, Choice, TF_Question, Essay_Question, QuizTaker, StudentAnswer, ContentAccess,
    Grade, Semester, CourseEnrollment, ActivityLog, InstructorRequest, SiteSettings,
    AdExemptUser, PaymentMethod, ModuleProgress, CertificateTemplate, StudentCertificate
)
from .forms import (
    LMSProfileForm, CourseForm, CourseModuleForm, CourseContentForm,
    QuizForm, MCQuestionForm, ChoiceForm, TFQuestionForm, EssayQuestionForm,
    GradeForm, CourseEnrollForm, EssayAnswerForm, InstructorRequestForm,
    ProgramForm, CertificateTemplateForm, MCAnswerForm, TFAnswerForm,
    LegalNameForm
)

from .forms import PaymentMethodForm
# Instructor: Manage Payment Methods
@login_required(login_url='login')
def instructor_payment_methods(request):
    """List and manage instructor's payment methods"""
    if not hasattr(request.user, 'lms_profile') or request.user.lms_profile.role != 'instructor':
        messages.error(request, _("You are not registered as an instructor."))
        return redirect('lms:lms_home')
    profile = request.user.lms_profile
    payment_methods = PaymentMethod.objects.filter(instructor=profile)
    return render(request, 'lms/instructor_payment_methods.html', {
        'payment_methods': payment_methods
    })

@login_required(login_url='login')
def add_payment_method(request):
    """Add a new payment method for instructor"""
    if not hasattr(request.user, 'lms_profile') or request.user.lms_profile.role != 'instructor':
        messages.error(request, _("You are not registered as an instructor."))
        return redirect('lms:lms_home')
    profile = request.user.lms_profile
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, request.FILES)
        if form.is_valid():
            payment_method = form.save(commit=False)
            payment_method.instructor = profile
            payment_method.save()
            messages.success(request, _(f"Payment method '{payment_method.name}' added."))
            return redirect('lms:instructor_payment_methods')
    else:
        form = PaymentMethodForm()
    return render(request, 'lms/add_payment_method.html', {'form': form})

@login_required(login_url='login')
def edit_payment_method(request, pk):
    """Edit an existing payment method for instructor"""
    if not hasattr(request.user, 'lms_profile') or request.user.lms_profile.role != 'instructor':
        messages.error(request, _("You are not registered as an instructor."))
        return redirect('lms:lms_home')
    profile = request.user.lms_profile
    payment_method = get_object_or_404(PaymentMethod, pk=pk, instructor=profile)
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, request.FILES, instance=payment_method)
        if form.is_valid():
            form.save()
            messages.success(request, _(f"Payment method '{payment_method.name}' updated."))
            return redirect('lms:instructor_payment_methods')
    else:
        form = PaymentMethodForm(instance=payment_method)
    return render(request, 'lms/edit_payment_method.html', {'form': form, 'payment_method': payment_method})

@login_required(login_url='login')
def delete_payment_method(request, pk):
    """Delete a payment method for instructor"""
    if not hasattr(request.user, 'lms_profile') or request.user.lms_profile.role != 'instructor':
        messages.error(request, _("You are not registered as an instructor."))
        return redirect('lms:lms_home')
    profile = request.user.lms_profile
    payment_method = get_object_or_404(PaymentMethod, pk=pk, instructor=profile)
    if request.method == 'POST':
        payment_method.delete()
        messages.success(request, _(f"Payment method deleted."))
        return redirect('lms:instructor_payment_methods')
    return render(request, 'lms/delete_payment_method.html', {'payment_method': payment_method})


def is_instructor(user):
    """
    Check if user is an instructor
    
    This function checks:
    1. If user has an LMS profile with instructor role
    2. If not, checks if they have an approved instructor request
    """
    try:
        # First check if they have the instructor role directly
        if hasattr(user, 'lms_profile') and user.lms_profile.role == 'instructor':
            return True
            
        # If not, check if they have an approved instructor request
        has_approved_request = InstructorRequest.objects.filter(
            user=user,
            status='approved'
        ).exists()
        
        # If they have an approved request but role not updated,
        # update their role now
        if has_approved_request and hasattr(user, 'lms_profile') and user.lms_profile.role != 'instructor':
            user.lms_profile.role = 'instructor'
            user.lms_profile.save()
            return True
            
        return False
    except Exception:
        return False


def is_student(user):
    """Check if user is a student"""
    try:
        return hasattr(user, 'lms_profile') and user.lms_profile.role == 'student'
    except:
        return False


def is_admin(user):
    """Check if user is an admin"""
    try:
        return hasattr(user, 'lms_profile') and user.lms_profile.role == 'admin'
    except:
        return False


def is_course_instructor(user, course):
    """
    Check if a user is an instructor for a specific course.
    Handles anonymous users and users without lms_profile safely.
    """
    if not user.is_authenticated:
        return False
    
    if not hasattr(user, 'lms_profile'):
        return False
        
    return is_admin(user) or course.instructors.filter(id=user.lms_profile.id).exists()


def get_question_kind(question):
    """Return the concrete question instance for multi-table inherited questions."""
    try:
        return question.mcquestion
    except MCQuestion.DoesNotExist:
        pass
    try:
        return question.tf_question
    except TF_Question.DoesNotExist:
        pass
    try:
        return question.essay_question
    except Essay_Question.DoesNotExist:
        pass
    return question


def can_manage_course(user, course):
    return is_course_instructor(user, course)


def _resolve_student_name(user):
    """Prefer the user's saved legal name, then full name, then username."""
    if not user:
        return ''
    profile = getattr(user, 'lms_profile', None)
    if profile and profile.has_legal_name:
        return profile.display_legal_name
    return (user.get_full_name() or user.username or '').strip()


def _resolve_instructor_name(course, template=None):
    """Build the instructor name shown on a certificate."""
    instructors = list(course.instructors.all()[:2]) if course else []
    names = []
    for instructor in instructors:
        if instructor.has_legal_name:
            names.append(instructor.display_legal_name)
        else:
            full = instructor.user.get_full_name() or instructor.user.username
            if full:
                names.append(full)
    if names:
        return ', '.join(names)
    if template and template.instructor_name:
        return template.instructor_name
    return 'Course Instructor'


def _build_certificate_previews(certificates):
    """Build a JSON-serializable list of certificate preview payloads.

    Used by views that include the certificate preview modal so the
    dashboard / course detail / quiz results can show an inline preview
    without a full page reload.
    """
    from django.urls import reverse
    from django.utils import timezone as _tz
    import json
    out = []
    for cert in certificates:
        template = cert.template
        out.append({
            'id': cert.certificate_id,
            'course_title': cert.course.title if cert.course else '',
            'student_name': _resolve_student_name(cert.student),
            'instructor_name': _resolve_instructor_name(cert.course, template),
            'issue_date': _tz.localtime(cert.issued_at).strftime('%B %d, %Y') if cert.issued_at else '',
            'organization_name': template.organization_name if template else 'ChuoSmart Academy',
            'certificate_title': template.title if template else 'Certificate of Completion',
            'detail_url': reverse('lms:certificate_detail', kwargs={'certificate_id': cert.certificate_id}),
            'download_url': reverse('lms:certificate_download', kwargs={'certificate_id': cert.certificate_id}),
        })
    return out


def _certificate_previews_json(certificates):
    """Render the certificate previews list as a </script>-safe JSON string.

    json.dumps handles the backslash and quote escaping, but it does NOT
    escape the `</` sequence — so a course title like `</script><img>`
    would break out of the surrounding <script type="application/json">
    block. We do a targeted replace here so the resulting text is still
    valid JSON for `JSON.parse(...)` on the client.
    """
    from django.utils.safestring import mark_safe
    import json
    payload = json.dumps(_build_certificate_previews(certificates))
    # Only neutralise the </script> close-tag and stray `<!--`. The result
    # is still valid JSON that JS can parse with JSON.parse().
    payload = payload.replace('</', '<\\/')
    return mark_safe(payload)


def _resolve_safe_next(request, fallback):
    """Return a safe relative URL for redirect-after-post.

    Only allow same-site paths to prevent open-redirect issues when the
    `next` query parameter is supplied by the user.
    """
    from django.urls import reverse
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return next_url
    try:
        return reverse(fallback)
    except Exception:
        return '/'


def legal_name_required(view_func):
    """Block the wrapped view until the user has saved their legal name.

    Used to gate certificate-related actions: when a student tries to
    download/issue a certificate or an instructor tries to act as a course
    instructor, they must first provide their full legal name.
    """
    from functools import wraps

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        profile = getattr(request.user, 'lms_profile', None)
        if profile is None:
            return view_func(request, *args, **kwargs)
        if profile.has_legal_name:
            return view_func(request, *args, **kwargs)

        from django.urls import reverse
        from urllib.parse import urlencode
        next_url = request.get_full_path()
        params = urlencode({'next': next_url, 'reason': 'certificate'})
        return redirect(f"{reverse('lms:set_legal_name')}?{params}")

    return _wrapped


@login_required(login_url='login')
def set_legal_name(request):
    """Prompt the user to enter their full legal name (one-time).

    After saving, the user is redirected to ``next`` (if safe) or to the
    appropriate dashboard based on their role.
    """
    profile, _ = LMSProfile.objects.get_or_create(user=request.user)

    fallback = 'lms:student_dashboard'
    if profile.role == 'instructor':
        fallback = 'lms:instructor_dashboard'
    elif profile.role == 'admin':
        fallback = 'lms:lms_home'

    if request.method == 'POST':
        form = LegalNameForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _("Thanks! Your legal name has been saved and will appear on your certificate."),
            )
            return redirect(_resolve_safe_next(request, fallback))
    else:
        form = LegalNameForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
        'reason': request.GET.get('reason', 'general'),
        'next': _resolve_safe_next(request, fallback),
        'already_set': profile.has_legal_name,
    }
    return render(request, 'lms/legal_name_prompt.html', context)


class InstructorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to restrict views to instructors only"""
    login_url = '/login/'  # Use the main app's login URL
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return is_instructor(self.request.user) or is_admin(self.request.user)
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        
        # If authenticated but not an instructor, check if they have a pending request
        messages.warning(self.request, _("You need instructor privileges to access this area."))
        
        # Check if user has a pending instructor request
        if hasattr(self.request.user, 'lms_profile'):
            pending_request = InstructorRequest.objects.filter(
                user=self.request.user, 
                status='pending'
            ).exists()
            
            if pending_request:
                messages.info(self.request, _("Your instructor request is pending approval."))
                return redirect('lms:instructor_request_status')
            else:
                messages.info(self.request, _("You can request to become an instructor."))
                return redirect('lms:request_instructor_role')
        
        return super().handle_no_permission()


class StudentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to restrict views to students only"""
    login_url = '/login/'  # Use the main app's login URL
    def test_func(self):
        return is_student(self.request.user) or is_admin(self.request.user)


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to restrict views to admins only"""
    login_url = '/login/'  # Use the main app's login URL
    def test_func(self):
        return is_admin(self.request.user)


def lms_home(request):
    """LMS home page view - accessible without login"""
    
    # Create profile if user is authenticated and doesn't have one
    user_profile = None
    if request.user.is_authenticated:
        if not hasattr(request.user, 'lms_profile'):
            LMSProfile.objects.create(
                user=request.user,
                role='student'  # Default role
            )
            messages.info(request, _("Welcome to the Learning Management System! Your student profile has been created."))
        
        user_profile = request.user.lms_profile
    
    # Get current semester
    current_semester = Semester.objects.filter(is_current_semester=True).first()
    
    context = {
        'user_profile': user_profile,
        'current_semester': current_semester,
        'is_authenticated': request.user.is_authenticated,
    }
    
    if request.user.is_authenticated:
        if is_student(request.user):
            # Get student's enrolled courses
            enrolled_courses = Course.objects.filter(courseenrollment__student=user_profile)
            
            # Get upcoming quizzes
            upcoming_quizzes = Quiz.objects.filter(
                course__in=enrolled_courses,
                draft=False,
                due_date__gt=timezone.now()
            ).order_by('due_date')[:5]
            
            context.update({
                'enrolled_courses': enrolled_courses,
                'upcoming_quizzes': upcoming_quizzes,
            })
        
        elif is_instructor(request.user):
            # Get courses taught by instructor
            teaching_courses = Course.objects.filter(instructors=user_profile)
            
            # Get recent quizzes created by instructor
            recent_quizzes = Quiz.objects.filter(course__instructors=user_profile).order_by('-timestamp')[:5]
            
            context.update({
                'teaching_courses': teaching_courses,
                'recent_quizzes': recent_quizzes,
            })
        
        elif is_admin(request.user):
            # Get system statistics
            stats = {
                'total_courses': Course.objects.count(),
                'total_students': LMSProfile.objects.filter(role='student').count(),
                'total_instructors': LMSProfile.objects.filter(role='instructor').count(),
                'total_quizzes': Quiz.objects.count(),
            }
            
            # Get recent activity logs
            recent_activities = ActivityLog.objects.all()[:10]
            
            context.update({
                'stats': stats,
                'recent_activities': recent_activities,
            })
    else:
        # For unauthenticated users, show featured courses
        featured_courses = Course.objects.filter(is_pinned=True).order_by('?')[:6]
        context.update({
            'featured_courses': featured_courses,
        })
    
    return render(request, 'lms/home.html', context)


class ProgramListView(ListView):
    """List all programs"""
    model = Program
    template_name = 'lms/program_list.html'
    context_object_name = 'programs'


class ProgramDetailView(DetailView):
    """Show details of a program"""
    model = Program
    template_name = 'lms/program_detail.html'
    context_object_name = 'program'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = self.get_object()
        context['courses'] = Course.objects.filter(program=program).order_by('?')
        return context


class CourseListView(ListView):
    """List all courses - accessible without login"""
    model = Course
    template_name = 'lms/course_list.html'
    context_object_name = 'courses'
    paginate_by = 10
    
    def get_queryset(self):
        # Randomize the base queryset so the course list feels fresh across layouts.
        queryset = Course.objects.all().order_by('?')
        
        # Filter by course type if provided
        course_type = self.request.GET.get('course_type')
        if course_type:
            queryset = queryset.filter(course_type=course_type)
        
        # Filter by semester if provided
        semester = self.request.GET.get('semester')
        if semester:
            queryset = queryset.filter(semester=semester)
        
        # Filter by program if provided
        program = self.request.GET.get('program')
        if program:
            queryset = queryset.filter(program__id=program)
        
        # Filter by level if provided
        level = self.request.GET.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Search query
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(code__icontains=query) |
                Q(summary__icontains=query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['programs'] = Program.objects.all()
        context['is_authenticated'] = self.request.user.is_authenticated
        context['current_filters'] = {
            'semester': self.request.GET.get('semester', ''),
            'program': self.request.GET.get('program', ''),
            'level': self.request.GET.get('level', ''),
            'course_type': self.request.GET.get('course_type', ''),
            'q': self.request.GET.get('q', ''),
        }
        context['course_listing_json_ld'] = {
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            'name': 'Course List',
            'description': 'Browse free and paid courses for students in Tanzania.',
        }
        return context


class CourseDetailView(DetailView):
    """Show details of a course - accessible without login"""
    model = Course
    template_name = 'lms/course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        
        # Get course modules with contents - accessible to everyone
        modules = CourseModule.objects.filter(course=course).prefetch_related('contents')
        
        # Get quizzes for this course. Personalized AI quizzes must not leak
        # into another learner's course list.
        quizzes = Quiz.objects.filter(course=course, draft=False, generated_for__isnull=True)
        
        # Check if user is enrolled and get enrollment status
        is_enrolled = False
        student_profile = None
        enrollment = None
        payment_status = None
        has_access = course.is_free
        can_view_content = False
        
        if self.request.user.is_authenticated and hasattr(self.request.user, 'lms_profile'):
            student_profile = self.request.user.lms_profile
            try:
                enrollment = CourseEnrollment.objects.get(
                    student=student_profile,
                    course=course
                )
                is_enrolled = True
                payment_status = enrollment.payment_status
                # For enrolled users: access depends on course type and payment status
                has_access = course.is_free or payment_status == 'approved'
            except CourseEnrollment.DoesNotExist:
                has_access = course.is_free
        
        # Check if user is instructor for this course
        is_course_instructor = False
        if self.request.user.is_authenticated and hasattr(self.request.user, 'lms_profile'):
            is_course_instructor = course.instructors.filter(id=self.request.user.lms_profile.id).exists()
            # Instructors always have access
            if is_course_instructor:
                has_access = True
        
        # Get course progress if user is enrolled and has access
        course_progress = None
        module_states = []
        issued_certificate = None
        if is_enrolled and student_profile and has_access:
            from .utils import (
                calculate_course_progress,
                ensure_course_learning_records,
                get_module_progress_states,
                issue_certificate_if_eligible,
            )
            ensure_course_learning_records(course, student_profile)
            quizzes = Quiz.objects.filter(
                Q(course=course),
                Q(draft=False),
                Q(generated_for=student_profile) | Q(generated_for__isnull=True),
            ).order_by('module__order', 'module__id', 'title', 'id')
            course_progress = calculate_course_progress(course, student_profile)
            module_states = get_module_progress_states(course, student_profile)
            if course_progress.get('course_completed'):
                issued_certificate = issue_certificate_if_eligible(course, student_profile)
            
        # Add is_free status to context
        context['is_free'] = course.is_free
        
        # If user is instructor, get progress data for all enrolled students
        students_progress = None
        if is_course_instructor:
            from .utils import get_all_enrolled_students_progress
            students_progress = get_all_enrolled_students_progress(course)
            from .utils import get_module_progress_states
            module_states = get_module_progress_states(course, self.request.user.lms_profile)
            quizzes = Quiz.objects.filter(
                course=course,
                draft=False,
                generated_for__isnull=True,
            ).order_by('module__order', 'module__id', 'title', 'id')
        
        # Get payment methods for premium courses
        payment_methods = None
        if not course.is_free:
            payment_methods = PaymentMethod.objects.filter(is_active=True)
        
        context.update({
            'modules': modules,
            'quizzes': quizzes,
            'is_enrolled': is_enrolled,
            'is_course_instructor': is_course_instructor,
            'course_progress': course_progress,
            'module_states': module_states,
            'issued_certificate': issued_certificate,
            'students_progress': students_progress,
            'has_access': has_access,
            'can_view_content': can_view_content,  # Allow unauthenticated preview
            'is_authenticated': self.request.user.is_authenticated,
            'payment_status': payment_status,
            'enrollment': enrollment,
            'payment_methods': payment_methods,
            'certificate_downloads_enabled': bool(getattr(settings, 'CERTIFICATE_DOWNLOADS_ENABLED', False)),
            'certificate_previews': _certificate_previews_json([issued_certificate]) if issued_certificate else '[]',
        })

        from django.utils.html import strip_tags
        from django.template.defaultfilters import truncatechars
        from django.templatetags.static import static
        domain = getattr(settings, 'SITE_DOMAIN', 'chuosmart.com')
        base_url = f"https://{domain}"
        course_url = self.request.build_absolute_uri(course.get_absolute_url() if hasattr(course, 'get_absolute_url') else f'/lms/courses/{course.slug}/')
        course_description_plain = truncatechars(
            strip_tags(course.summary or course.content or ''), 200
        )
        context['course_json_ld'] = {
            '@context': 'https://schema.org',
            '@type': 'Course',
            'name': course.title or '',
            'description': course_description_plain,
            'provider': {
                '@type': 'Organization',
                'name': 'ChuoSmart',
                'sameAs': base_url,
            },
            'url': course_url,
            'inLanguage': 'en',
            'educationalCredentialAwarded': 'Certificate',
        }
        context['course_breadcrumb_json_ld'] = {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {
                    '@type': 'ListItem',
                    'position': 1,
                    'name': 'Home',
                    'item': f"{base_url}/",
                },
                {
                    '@type': 'ListItem',
                    'position': 2,
                    'name': 'Courses',
                    'item': f"{base_url}{reverse('lms:course_list')}",
                },
                {
                    '@type': 'ListItem',
                    'position': 3,
                    'name': course.title or '',
                    'item': course_url,
                },
            ],
        }

        return context


@login_required(login_url='login')
def enroll_course(request, slug):
    """Enroll in a course"""
    course = get_object_or_404(Course, slug=slug)
    
    # Create LMS profile if not exists
    if not hasattr(request.user, 'lms_profile'):
        profile = LMSProfile.objects.create(user=request.user, role='student')
    else:
        profile = request.user.lms_profile
    
    # Check if already enrolled
    enrollment = CourseEnrollment.objects.filter(student=profile, course=course).first()
    if enrollment:
        messages.info(request, _("You are already enrolled in this course."))
        return redirect('lms:course_detail', slug=course.slug)
    
    # For free courses, enroll immediately
    if course.is_free:
        enrollment = CourseEnrollment.objects.create(
            student=profile, 
            course=course,
            payment_status='not_required'
        )
        # Log activity
        ActivityLog.objects.create(
            message=_(f"User {request.user.username} enrolled in free course {course.title}.")
        )
        messages.success(request, _(f"You have successfully enrolled in {course.title}."))
        return redirect('lms:course_detail', slug=course.slug)
    else:
        # For paid courses, redirect to payment form (do not create enrollment yet)
        return redirect('lms:payment_form', slug=course.slug)


@login_required(login_url='login')
def unenroll_course(request, slug):
    """Unenroll from a course"""
    course = get_object_or_404(Course, slug=slug)
    
    if not hasattr(request.user, 'lms_profile'):
        messages.error(request, _("You don't have an LMS profile."))
        return redirect('lms:course_detail', slug=course.slug)
    
    profile = request.user.lms_profile
    
    # Check if enrolled
    enrollment = CourseEnrollment.objects.filter(student=profile, course=course).first()
    if not enrollment:
        messages.info(request, _("You are not enrolled in this course."))
        return redirect('lms:course_detail', slug=course.slug)
    
    # Delete enrollment
    enrollment.delete()
    
    # Log activity
    ActivityLog.objects.create(
        message=_(f"User {request.user.username} unenrolled from course {course.title}.")
    )
    
    messages.success(request, _(f"You have successfully unenrolled from {course.title}."))
    return redirect('lms:course_list')


class QuizDetailView(DetailView):
    """Show details of a quiz - accessible without login"""
    model = Quiz
    template_name = 'lms/quiz_detail.html'
    context_object_name = 'quiz'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.get_object()
        
        # Default values
        can_take_quiz = False
        is_instructor = False
        is_enrolled = False
        previous_attempts = None
        completed_attempt = None
        user_score = None
        module_locked = False
        generation_status = getattr(quiz, 'generation_status', 'ready')
        generation_message = getattr(quiz, 'generation_message', '')
        quiz_is_ready = bool(quiz.questions.exists()) and generation_status == 'ready'
        
        context['is_authenticated'] = self.request.user.is_authenticated
        
        if self.request.user.is_authenticated and hasattr(self.request.user, 'lms_profile'):
            profile = self.request.user.lms_profile
            
            # Check if enrolled in course
            is_enrolled = CourseEnrollment.objects.filter(
                student=profile,
                course=quiz.course
            ).exists()
            
            # Check if instructor
            is_instructor = is_course_instructor(self.request.user, quiz.course)
            
            # Get previous attempts
            previous_attempts = QuizTaker.objects.filter(
                user=profile,
                quiz=quiz
            ).order_by('-date_started')
            
            # Get the most recent completed attempt if any
            completed_attempt = previous_attempts.filter(completed=True).first()
            if completed_attempt:
                user_score = completed_attempt.get_score_percentage()
            
            if is_enrolled:
                if quiz.module and getattr(quiz.module, 'skip_assessment', False):
                    module_locked = False
                    can_take_quiz = False
                elif quiz.module:
                    from .utils import is_module_unlocked
                    module_locked = not is_module_unlocked(quiz.module, profile)
                # Do not block taking the quiz based on module lock status.
                # Check single attempt restriction
                if not quiz_is_ready:
                    can_take_quiz = False
                elif quiz.single_attempt and completed_attempt and completed_attempt.score >= quiz.pass_mark:
                    can_take_quiz = False
                else:
                    can_take_quiz = True
        
        # Check if quiz is past due date
        is_past_due = False
        if quiz.due_date and timezone.now() > quiz.due_date:
            is_past_due = True
            can_take_quiz = False
        
        context.update({
            'user_can_take_quiz': can_take_quiz,
            'user_is_instructor': is_instructor,
            'is_enrolled': is_enrolled,
            'not_enrolled': not is_enrolled,
            'previous_attempts': previous_attempts,
            'completed_attempt': completed_attempt,
            'has_already_taken': completed_attempt is not None,
            'user_score': user_score,
            'module_locked': module_locked,
            'is_past_due': is_past_due,
            'past_due': is_past_due,
            'generation_status': generation_status,
            'generation_message': generation_message,
            'quiz_is_ready': quiz_is_ready,
            'is_generating': generation_status in {'pending', 'processing'},
            'generation_failed': generation_status == 'failed' and not quiz_is_ready,
        })
        
        return context


@login_required(login_url='login')
def start_quiz(request, slug):
    """Start a quiz"""
    quiz = get_object_or_404(Quiz, slug=slug)
    
    if not hasattr(request.user, 'lms_profile'):
        messages.error(request, _("You don't have an LMS profile."))
        return redirect('lms:quiz_detail', slug=quiz.slug)
    
    profile = request.user.lms_profile
    
    # Check if enrolled in course
    is_enrolled = CourseEnrollment.objects.filter(
        student=profile,
        course=quiz.course
    ).exists()
    
    if not is_enrolled:
        messages.error(request, _("You must be enrolled in the course to take this quiz."))
        return redirect('lms:quiz_detail', slug=quiz.slug)

    if quiz.module:
        if getattr(quiz.module, 'skip_assessment', False):
            messages.info(request, _("This module does not require an assessment."))
            return redirect('lms:course_detail', slug=quiz.course.slug)

        if quiz.generation_status in {'pending', 'processing'} or not quiz.questions.exists():
            messages.info(request, _("Your personalized quiz is still being prepared. Please check the progress page in a moment."))
            return redirect('lms:quiz_detail', slug=quiz.slug)

        # Allow taking mastery checks even if the module is locked.
        # The module lock still applies to content access, but assessments
        # can be taken to qualify for unlocking subsequent modules.
    
    # Check single attempt restriction
    completed_attempt = QuizTaker.objects.filter(user=profile, quiz=quiz, completed=True).first()
    if quiz.single_attempt and completed_attempt and completed_attempt.score >= quiz.pass_mark:
        messages.error(request, _("You have already passed this quiz."))
        return redirect('lms:quiz_detail', slug=quiz.slug)
    
    # Check if quiz is past due date
    if quiz.due_date and timezone.now() > quiz.due_date:
        messages.error(request, _("This quiz is past its due date."))
        return redirect('lms:quiz_detail', slug=quiz.slug)

    if not quiz.questions.exists():
        messages.error(request, _("This quiz does not have any questions yet."))
        return redirect('lms:quiz_detail', slug=quiz.slug)
    
    quiz_taker, created = QuizTaker.objects.get_or_create(user=profile, quiz=quiz)

    if not created and quiz_taker.completed and quiz_taker.score < quiz.pass_mark:
        quiz_taker.answers.all().delete()
        quiz_taker.completed = False
        quiz_taker.score = 0
        quiz_taker.date_started = timezone.now()
        quiz_taker.date_completed = None
        quiz_taker.save()
    elif created:
        quiz_taker.date_started = timezone.now()
        quiz_taker.save()
    
    # Redirect to first question
    return redirect('lms:quiz_question', quiz_id=quiz.id, quiz_taker_id=quiz_taker.id, question_number=1)


@login_required(login_url='login')
def quiz_question(request, quiz_id, quiz_taker_id, question_number):
    """Show a quiz question and process answers"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz_taker = get_object_or_404(QuizTaker, id=quiz_taker_id, user=request.user.lms_profile)
    
    # Get all questions for this quiz
    if quiz.random_order:
        questions = list(Question.objects.filter(quiz=quiz).order_by('?'))
    else:
        questions = list(Question.objects.filter(quiz=quiz).order_by('order', 'id'))
    
    # Check if question_number is valid
    if question_number < 1 or question_number > len(questions):
        messages.error(request, _("Invalid question number."))
        return redirect('lms:quiz_detail', slug=quiz.slug)
    
    # Get current question
    question = get_question_kind(questions[question_number - 1])
    
    # Handle form submission
    if request.method == 'POST':
        # Process different question types
        if isinstance(question, MCQuestion):
            # Handle multiple choice
            form = MCAnswerForm(request.POST, question=question)
            if form.is_valid():
                selected_choice = form.cleaned_data['choice']
                is_correct = question.check_if_correct(selected_choice)
                
                # Save answer
                StudentAnswer.objects.update_or_create(
                    quiz_taker=quiz_taker,
                    question=question,
                    defaults={
                        'mc_answer': selected_choice,
                        'is_correct': is_correct
                    }
                )
            
        elif isinstance(question, TF_Question):
            # Handle true/false
            form = TFAnswerForm(request.POST)
            if form.is_valid():
                selected_answer = form.cleaned_data['answer'] == 'true'
                is_correct = selected_answer == question.correct
                
                # Save answer
                StudentAnswer.objects.update_or_create(
                    quiz_taker=quiz_taker,
                    question=question,
                    defaults={
                        'tf_answer': selected_answer,
                        'is_correct': is_correct
                    }
                )
        
        elif isinstance(question, Essay_Question):
            # Handle essay
            form = EssayAnswerForm(request.POST, request.FILES)
            if form.is_valid():
                # Save answer
                StudentAnswer.objects.update_or_create(
                    quiz_taker=quiz_taker,
                    question=question,
                    defaults={
                        'essay_text_answer': form.cleaned_data.get('answer_text', ''),
                        'essay_file_answer': form.cleaned_data.get('answer_file', None),
                        'is_correct': None
                    }
                )
        
        # Move to next question or finish quiz
        if question_number < len(questions):
            return redirect('lms:quiz_question', 
                           quiz_id=quiz.id,
                           quiz_taker_id=quiz_taker.id, 
                           question_number=question_number + 1)
        else:
            # Complete quiz
            return redirect('lms:complete_quiz', quiz_taker_id=quiz_taker.id)
    
    # Prepare question context
    context = {
        'quiz': quiz,
        'question': question,
        'question_number': question_number,
        'total_questions': len(questions),
    }
    
    # Add specific context based on question type
    if isinstance(question, MCQuestion):
        context['choices'] = Choice.objects.filter(question=question)
        # Check if user already answered
        previous_answer = StudentAnswer.objects.filter(quiz_taker=quiz_taker, question=question).first()
        if previous_answer:
            context['previous_answer'] = previous_answer.mc_answer
    
    elif isinstance(question, TF_Question):
        # Check if user already answered
        previous_answer = StudentAnswer.objects.filter(quiz_taker=quiz_taker, question=question).first()
        if previous_answer and previous_answer.tf_answer is not None:
            context['previous_answer'] = previous_answer.tf_answer
    
    elif isinstance(question, Essay_Question):
        # Essay form
        context['essay_form'] = EssayAnswerForm()
        # Check if user already answered
        previous_answer = StudentAnswer.objects.filter(quiz_taker=quiz_taker, question=question).first()
        if previous_answer:
            context['previous_text_answer'] = previous_answer.essay_text_answer
            context['previous_file_answer'] = previous_answer.essay_file_answer
    
    return render(request, 'lms/quiz_question.html', context)


@login_required(login_url='login')
def complete_quiz(request, quiz_taker_id):
    """Complete a quiz and show results"""
    quiz_taker = get_object_or_404(QuizTaker, id=quiz_taker_id, user=request.user.lms_profile)
    quiz = quiz_taker.quiz
    
    # If already completed, just show the results
    if quiz_taker.completed:
        return redirect('lms:quiz_results', quiz_taker_id=quiz_taker.id)
    
    # Calculate score
    total_questions = Question.objects.filter(quiz=quiz).count()
    correct_answers = StudentAnswer.objects.filter(quiz_taker=quiz_taker, is_correct=True).count()
    
    # Handle case where there are essay questions
    essay_questions = Essay_Question.objects.filter(quiz=quiz).count()
    total_non_essay = total_questions - essay_questions
    
    if total_non_essay > 0:
        score_percentage = (correct_answers / total_non_essay) * 100
    else:
        # If only essay questions, score will be determined by instructor
        score_percentage = 0
    
    # Update quiz taker
    quiz_taker.score = score_percentage
    quiz_taker.completed = True
    quiz_taker.date_completed = timezone.now()
    quiz_taker.save()

    module_progress = None
    issued_certificate = None
    next_module = None
    unlock_message = None
    
    from django.db import transaction
    with transaction.atomic():
        if quiz.module:
            from .utils import update_module_assessment_completion, update_module_content_completion, issue_certificate_if_eligible, get_next_module
            update_module_content_completion(quiz.module, quiz_taker.user)
            module_progress = update_module_assessment_completion(quiz_taker)
            if module_progress and module_progress.unlocks_next:
                issued_certificate = issue_certificate_if_eligible(quiz.course, quiz_taker.user)
                next_module = get_next_module(quiz.module)
                if next_module:
                    unlock_message = _(
                        "You unlocked %(module)s. It is now available in this course."
                    ) % {'module': next_module.title}
                else:
                    unlock_message = _("You unlocked the final module in this course.")
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"User {request.user.username} completed quiz '{quiz.title}' with score {score_percentage:.1f}%.")
        )

        if quiz_taker.passed:
            if unlock_message:
                messages.success(request, unlock_message)
            if issued_certificate:
                messages.success(request, _("Congratulations! Your course certificate has been issued."))
            if next_module:
                return redirect(f"{reverse('lms:course_detail', kwargs={'slug': quiz.course.slug})}#collapse{next_module.id}")
        else:
            messages.warning(request, _("You need at least 70% to unlock the next module. Review this module and try again."))
        
        return redirect('lms:quiz_results', quiz_taker_id=quiz_taker.id)


@login_required(login_url='login')
def quiz_results(request, quiz_taker_id):
    """Show quiz results"""
    quiz_taker = get_object_or_404(QuizTaker, id=quiz_taker_id, user=request.user.lms_profile)
    quiz = quiz_taker.quiz
    
    # Get all answers
    answers = StudentAnswer.objects.filter(quiz_taker=quiz_taker).select_related('question')
    
    # Check if passed
    passed = quiz_taker.score >= quiz.pass_mark
    
    # Issue certificate if course is now fully completed
    issued_certificate = None
    if passed and quiz.module and hasattr(request.user, 'lms_profile'):
        from .utils import is_course_completed, issue_certificate_if_eligible
        if is_course_completed(quiz.course, request.user.lms_profile):
            issued_certificate = issue_certificate_if_eligible(quiz.course, request.user.lms_profile)
    
    context = {
        'quiz_taker': quiz_taker,
        'quiz': quiz,
        'answers': answers,
        'passed': passed,
        'issued_certificate': issued_certificate,
        'show_answers': quiz.answers_at_end or not quiz.exam_paper,
        'certificate_downloads_enabled': bool(getattr(settings, 'CERTIFICATE_DOWNLOADS_ENABLED', False)),
        'certificate_previews': _certificate_previews_json([issued_certificate]) if issued_certificate else '[]',
    }

    return render(request, 'lms/quiz_results.html', context)


def course_content_detail(request, course_slug, content_id):
    """Show course content details - accessible without login"""
    course = get_object_or_404(Course, slug=course_slug)
    content = get_object_or_404(CourseContent, id=content_id, module__course=course)
    
    # Check if user is enrolled or is instructor
    is_enrolled = False
    is_instructor = False
    profile = None

    if request.user.is_authenticated and hasattr(request.user, 'lms_profile'):
        profile = request.user.lms_profile
        is_enrolled = CourseEnrollment.objects.filter(student=profile, course=course).exists()
        is_instructor = course.instructors.filter(id=profile.id).exists()

    if not is_instructor:
        if not request.user.is_authenticated:
            messages.info(request, _("Login and enroll to open course modules."))
            return redirect_to_login(request.get_full_path(), reverse('login'))
        if not is_enrolled:
            messages.info(request, _("Enroll in this course to open its modules."))
            return redirect('lms:enroll_course', slug=course.slug)
        if not course.user_has_access(request.user):
            messages.warning(request, _("Your payment must be approved before you can access this course."))
            return redirect('lms:course_detail', slug=course.slug)

        from .utils import is_module_unlocked
        if not is_module_unlocked(content.module, profile):
            messages.error(request, _("This module is locked. Complete the previous module assessment with at least 70% first."))
            return redirect('lms:course_detail', slug=course.slug)

    # If user attempts to mark content complete, require login and enrollment to save progress
    mark_complete = request.GET.get('mark_complete') == 'true'
    if mark_complete:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('login'))
        # Ensure user has a profile
        if not profile:
            messages.error(request, _("You need an LMS profile to save progress."))
            return redirect('lms:lms_home')
        # If user is not enrolled and not an instructor, ask them to enroll
        if not is_enrolled and not is_instructor:
            messages.info(request, _("You need to enroll in this course to save progress."))
            return redirect('lms:enroll_course', slug=course.slug)
    
    # Allow access to all: unauthenticated users, students, and instructors
    # Track content access for authenticated students (not instructors or staff)
    if is_enrolled and not is_instructor and not request.user.is_staff and profile:
        content_access, created = ContentAccess.objects.get_or_create(
            student=profile,
            content=content
        )

        # Mark as completed if it's a request from the "mark complete" button
        if mark_complete:
            content_access.mark_complete()
            from .utils import update_module_content_completion
            progress = update_module_content_completion(content.module, profile)
            if progress.content_completed and not progress.assessment_passed:
                from .ai_assessments import queue_module_assessment_generation
                quiz = queue_module_assessment_generation(content.module, student=profile)
                if quiz is None:
                    messages.success(request, _("Content completed! This overview module does not require a quiz."))
                    return redirect('lms:content_detail', course_slug=course_slug, content_id=content_id)
                messages.success(request, _("Content completed. Your personalized mastery check is being prepared now."))
                return redirect('lms:quiz_detail', slug=quiz.slug)
            messages.success(request, _("Content marked as completed!"))
            return redirect('lms:content_detail', course_slug=course_slug, content_id=content_id)
    
    # Check if this content is completed by the student
    content_completed = False
    if profile and is_enrolled:
        content_completed = ContentAccess.objects.filter(
            student=profile,
            content=content,
            completed=True
        ).exists()
    
    context = {
        'course': course,
        'content': content,
        'module': content.module,
        'content_completed': content_completed,
        'is_enrolled': is_enrolled,
        'is_authenticated': request.user.is_authenticated,
        'can_save_progress': bool(profile and is_enrolled and not is_instructor),
    }
    
    return render(request, 'lms/course_content_detail.html', context)


class CourseCreateView(InstructorRequiredMixin, CreateView):
    """Create a new course"""
    model = Course
    form_class = CourseForm
    template_name = 'lms/course_form.html'
    
    # Explicitly tell the view to accept file uploads
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'files': self.request.FILES,
            })
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if there are any programs
        context['has_programs'] = Program.objects.exists()
        context['program_form'] = ProgramForm()
        return context
    
    def post(self, request, *args, **kwargs):
        # Check if this is a program creation submission
        if 'create_program' in request.POST:
            program_form = ProgramForm(request.POST)
            if program_form.is_valid():
                program = program_form.save()
                messages.success(request, _(f"Program '{program.title}' created successfully."))
                # Redirect back to the course creation page
                return redirect('lms:course_create')
            else:
                # If program form is invalid, show it with the course form
                self.object = None
                return self.render_to_response(
                    self.get_context_data(
                        form=self.get_form(),
                        program_form=program_form
                    )
                )
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Check if we need to create a program
        if not Program.objects.exists() and 'program' not in form.cleaned_data:
            messages.error(self.request, _("You must create a program before creating a course."))
            return self.form_invalid(form)
            
        # Set instructor
        response = super().form_valid(form)
        course = self.object
        course.instructors.add(self.request.user.lms_profile)
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {self.request.user.username} created course '{course.title}'.")
        )
        
        messages.success(self.request, _("Course created successfully."))
        return response


class CourseUpdateView(InstructorRequiredMixin, UpdateView):
    """Update an existing course"""
    model = Course
    form_class = CourseForm
    template_name = 'lms/course_form.html'
    
    # Explicitly tell the view to accept file uploads
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'files': self.request.FILES,
            })
        return kwargs
    
    def get_queryset(self):
        # Limit to courses where user is instructor
        if is_admin(self.request.user):
            return Course.objects.all()
        return Course.objects.filter(instructors=self.request.user.lms_profile)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['program_form'] = ProgramForm()
        return context
    
    def post(self, request, *args, **kwargs):
        # Check if this is a program creation submission
        if 'create_program' in request.POST:
            program_form = ProgramForm(request.POST)
            if program_form.is_valid():
                program = program_form.save()
                messages.success(request, _(f"Program '{program.title}' created successfully."))
                # Redirect back to the course update page
                return redirect('lms:course_update', slug=self.get_object().slug)
            else:
                # If program form is invalid, show it with the course form
                self.object = self.get_object()
                return self.render_to_response(
                    self.get_context_data(
                        form=self.get_form(),
                        program_form=program_form
                    )
                )

        # Set self.object before processing the form
        self.object = self.get_object()
        
        # Get the form instance with POST data and FILES
        form = self.get_form()
        
        # Print debugging information about the request
        print(f"FILES in request: {request.FILES}")
        print(f"Image field in form: {form.fields.get('image')}")
        
        # Check if the form has an image file
        if form.is_valid():
            return self.form_valid(form)
        else:
            print(f"Form errors: {form.errors}")
            return self.form_invalid(form)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {self.request.user.username} updated course '{self.object.title}'.")
        )
        
        messages.success(self.request, _("Course updated successfully."))
        return response


class CourseModuleCreateView(InstructorRequiredMixin, CreateView):
    """Create a new course module"""
    model = CourseModule
    form_class = CourseModuleForm
    template_name = 'lms/module_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, _("You need to log in to access this page."))
            return self.handle_no_permission()
        
        # Then check if the user has an LMS profile
        if not hasattr(request.user, 'lms_profile'):
            messages.error(request, _("You don't have an LMS profile. Please contact an administrator."))
            return redirect('lms:lms_home')
            
        # Now get the course
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        
        # Check if user is instructor for this course
        if not is_admin(request.user) and not self.course.instructors.filter(id=request.user.lms_profile.id).exists():
            messages.error(request, _("You are not an instructor for this course."))
            return redirect('lms:course_detail', slug=self.course.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.course = self.course
        response = super().form_valid(form)
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {self.request.user.username} added module '{form.instance.title}' to course '{self.course.title}'.")
        )
        
        messages.success(self.request, _("Module created successfully."))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context
    
    def get_success_url(self):
        return reverse('lms:course_detail', kwargs={'slug': self.course.slug})


class CourseModuleUpdateView(InstructorRequiredMixin, UpdateView):
    """Update an existing course module"""
    model = CourseModule
    form_class = CourseModuleForm
    template_name = 'lms/module_form.html'
    pk_url_kwarg = 'module_id'
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, _("You need to log in to access this page."))
            return self.handle_no_permission()
        
        # Then check if the user has an LMS profile
        if not hasattr(request.user, 'lms_profile'):
            messages.error(request, _("You don't have an LMS profile. Please contact an administrator."))
            return redirect('lms:lms_home')
            
        # Now get the course
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        
        # Check if user is instructor for this course
        if not is_admin(request.user) and not self.course.instructors.filter(id=request.user.lms_profile.id).exists():
            messages.error(request, _("You are not an instructor for this course."))
            return redirect('lms:course_detail', slug=self.course.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return CourseModule.objects.filter(course=self.course)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {self.request.user.username} updated module '{form.instance.title}' in course '{self.course.title}'.")
        )
        
        messages.success(self.request, _("Module updated successfully."))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context
    
    def get_success_url(self):
        return reverse('lms:course_detail', kwargs={'slug': self.course.slug})


class CourseModuleDeleteView(InstructorRequiredMixin, DeleteView):
    """Delete a course module"""
    model = CourseModule
    pk_url_kwarg = 'module_id'
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, _("You need to log in to access this page."))
            return self.handle_no_permission()
        
        # Then check if the user has an LMS profile
        if not hasattr(request.user, 'lms_profile'):
            messages.error(request, _("You don't have an LMS profile. Please contact an administrator."))
            return redirect('lms:lms_home')
            
        # Now get the course
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        
        # Check if user is instructor for this course
        if not is_admin(request.user) and not self.course.instructors.filter(id=request.user.lms_profile.id).exists():
            messages.error(request, _("You are not an instructor for this course."))
            return redirect('lms:course_detail', slug=self.course.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return CourseModule.objects.filter(course=self.course)
    
    def delete(self, request, *args, **kwargs):
        module = self.get_object()
        module_title = module.title
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {request.user.username} deleted module '{module_title}' from course '{self.course.title}'.")
        )
        
        messages.success(request, _("Module deleted successfully."))
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('lms:course_detail', kwargs={'slug': self.course.slug})


class CourseContentCreateView(InstructorRequiredMixin, CreateView):
    """Create new course content"""
    model = CourseContent
    form_class = CourseContentForm
    template_name = 'lms/content_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, _("You need to log in to access this page."))
            return self.handle_no_permission()
        
        # Then check if the user has an LMS profile
        if not hasattr(request.user, 'lms_profile'):
            messages.error(request, _("You don't have an LMS profile. Please contact an administrator."))
            return redirect('lms:lms_home')
            
        # Now get the course and module
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        self.module = get_object_or_404(CourseModule, id=self.kwargs['module_id'], course=self.course)
        
        # Check if user is instructor for this course
        if not is_admin(request.user) and not self.course.instructors.filter(id=request.user.lms_profile.id).exists():
            messages.error(request, _("You are not an instructor for this course."))
            return redirect('lms:course_detail', slug=self.course.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.module = self.module
        
        # Set proper fields based on content type
        content_type = form.cleaned_data.get('content_type')
        if content_type == 'text':
            form.instance.document = None
            form.instance.video_url = None
            form.instance.external_link = None
        elif content_type == 'document':
            form.instance.text_content = None
            form.instance.video_url = None
            form.instance.external_link = None
        elif content_type == 'video':
            form.instance.text_content = None
            form.instance.document = None
            form.instance.external_link = None
        elif content_type == 'link':
            form.instance.text_content = None
            form.instance.document = None
            form.instance.video_url = None
            
        response = super().form_valid(form)
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {self.request.user.username} added content '{form.instance.title}' to module '{self.module.title}'.")
        )
        
        messages.success(self.request, _("Content created successfully."))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        context['module'] = self.module
        return context
    
    def get_success_url(self):
        return reverse('lms:course_detail', kwargs={'slug': self.course.slug})


class CourseContentUpdateView(InstructorRequiredMixin, UpdateView):
    """Update existing course content"""
    model = CourseContent
    form_class = CourseContentForm
    template_name = 'lms/content_form.html'
    pk_url_kwarg = 'content_id'
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, _("You need to log in to access this page."))
            return self.handle_no_permission()
        
        # Then check if the user has an LMS profile
        if not hasattr(request.user, 'lms_profile'):
            messages.error(request, _("You don't have an LMS profile. Please contact an administrator."))
            return redirect('lms:lms_home')
            
        # Now get the course
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        
        # Check if user is instructor for this course
        if not is_admin(request.user) and not self.course.instructors.filter(id=request.user.lms_profile.id).exists():
            messages.error(request, _("You are not an instructor for this course."))
            return redirect('lms:course_detail', slug=self.course.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return CourseContent.objects.filter(module__course=self.course)
    
    def form_valid(self, form):
        # Set proper fields based on content type
        content_type = form.cleaned_data.get('content_type')
        if content_type == 'text':
            form.instance.document = None
            form.instance.video_url = None
            form.instance.external_link = None
        elif content_type == 'document':
            form.instance.text_content = None
            form.instance.video_url = None
            form.instance.external_link = None
        elif content_type == 'video':
            form.instance.text_content = None
            form.instance.document = None
            form.instance.external_link = None
        elif content_type == 'link':
            form.instance.text_content = None
            form.instance.document = None
            form.instance.video_url = None
            
        response = super().form_valid(form)
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {self.request.user.username} updated content '{form.instance.title}' in course '{self.course.title}'.")
        )
        
        messages.success(self.request, _("Content updated successfully."))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        context['module'] = self.object.module
        return context
    
    def get_success_url(self):
        return reverse('lms:course_detail', kwargs={'slug': self.course.slug})


class QuizCreateView(InstructorRequiredMixin, CreateView):
    """Queue an AI-generated module quiz.

    Manual quiz creation is intentionally disabled: all assessments are
    generated from module content.
    """
    model = Quiz
    form_class = QuizForm
    template_name = 'lms/quiz_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # First check if the user is authenticated and has an LMS profile
        # This is redundant with the InstructorRequiredMixin, but we'll keep it to be safe
        if not request.user.is_authenticated:
            messages.error(request, _("You must be logged in to create quizzes."))
            return redirect('login')  # Redirect to login page
            
        # Get the course
        self.course = get_object_or_404(Course, slug=self.kwargs['course_slug'])
        
        # Module is optional
        self.module = None
        module_id = self.kwargs.get('module_id')
        if module_id:
            self.module = get_object_or_404(CourseModule, id=module_id, course=self.course)
        
        # Check if user is instructor for this course, safely
        # First check if user is admin
        if is_admin(request.user):
            # Admin can access all courses
            pass
        elif not hasattr(request.user, 'lms_profile'):
            # User doesn't have an LMS profile
            messages.error(request, _("You don't have an LMS profile. Please contact an administrator."))
            return redirect('lms:course_detail', slug=self.course.slug)
        elif not self.course.instructors.filter(id=request.user.lms_profile.id).exists():
            # User is not an instructor for this course
            messages.error(request, _("You are not an instructor for this course."))
            return redirect('lms:course_detail', slug=self.course.slug)
        
        if not self.module:
            messages.info(
                request,
                _("Quizzes are generated by AI from individual modules. Open a module and use its assessment action."),
            )
            return redirect('lms:course_detail', slug=self.course.slug)

        if getattr(self.module, 'skip_assessment', False):
            messages.info(request, _("This module is configured to skip assessments."))
            return redirect('lms:course_detail', slug=self.course.slug)

        from .ai_assessments import queue_module_assessment_generation

        quiz = queue_module_assessment_generation(self.module, force=True)
        ActivityLog.objects.create(
            message=_(
                f"Instructor {self.request.user.username} queued AI quiz generation for module "
                f"'{self.module.title}' in course '{self.course.title}'."
            )
        )
        messages.success(request, _("AI assessment generation has been queued for this module."))
        if quiz:
            return redirect('lms:quiz_detail', slug=quiz.slug)
        return redirect('lms:course_detail', slug=self.course.slug)
    
    def form_valid(self, form):
        form.instance.course = self.course
        if self.module:
            form.instance.module = self.module
        
        response = super().form_valid(form)
        
        # Create activity log
        ActivityLog.objects.create(
            message=_(f"Instructor {self.request.user.username} created quiz '{form.instance.title}' for course '{self.course.title}'.")
        )
        
        messages.success(self.request, _("Quiz created successfully. Now add some questions."))
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        context['module'] = self.module
        return context
    
    def get_success_url(self):
        return reverse('lms:quiz_detail', kwargs={'slug': self.object.slug})


@login_required(login_url='login')
def add_mc_question(request, quiz_id):
    """Manual question authoring is disabled. Quizzes are generated by AI from module content."""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    messages.info(request, _("Manual question authoring is disabled. Quizzes are generated by AI from module content."))
    return redirect('lms:quiz_detail', slug=quiz.slug)


@login_required(login_url='login')
def add_tf_question(request, quiz_id):
    """Manual question authoring is disabled. Quizzes are generated by AI from module content."""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    messages.info(request, _("Manual question authoring is disabled. Quizzes are generated by AI from module content."))
    return redirect('lms:quiz_detail', slug=quiz.slug)


@login_required(login_url='login')
def add_essay_question(request, quiz_id):
    """Manual question authoring is disabled. Quizzes are generated by AI from module content."""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    messages.info(request, _("Manual question authoring is disabled. Quizzes are generated by AI from module content."))
    return redirect('lms:quiz_detail', slug=quiz.slug)

    # Check permissions
    if not is_admin(request.user) and not quiz.course.instructors.filter(id=request.user.lms_profile.id).exists():
        messages.error(request, _("You are not authorized to add questions to this quiz."))
        return redirect('lms:quiz_detail', slug=quiz.slug)

    if request.method == 'POST':
        form = EssayQuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()

            messages.success(request, _("Essay question added successfully."))
            return redirect('lms:quiz_detail', slug=quiz.slug)
    else:
        form = EssayQuestionForm()
    
    context = {
        'form': form,
        'quiz': quiz,
        'question_type': 'Essay'
    }
    
    return render(request, 'lms/essay_question_form.html', context)


class GradeListView(LoginRequiredMixin, ListView):
    login_url = '/login/'
    """List grades for a course"""
    model = Grade
    template_name = 'lms/grade_list.html'
    context_object_name = 'grades'
    
    def get_queryset(self):
        # For students, show only their own grades
        if is_student(self.request.user):
            return Grade.objects.filter(student=self.request.user.lms_profile)
        
        # For instructors, show grades for their courses
        elif is_instructor(self.request.user):
            return Grade.objects.filter(course__instructors=self.request.user.lms_profile)
        
        # For admins, show all grades
        else:
            return Grade.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group grades by course and semester
        grades_by_course = {}
        for grade in self.get_queryset():
            course_key = f"{grade.course.title} ({grade.semester})"
            if course_key not in grades_by_course:
                grades_by_course[course_key] = []
            grades_by_course[course_key].append(grade)
        
        context['grades_by_course'] = grades_by_course
        context['is_student'] = is_student(self.request.user)
        
        return context


class CertificateTemplateListView(InstructorRequiredMixin, ListView):
    model = CertificateTemplate
    template_name = 'lms/certificates/template_list.html'
    context_object_name = 'templates'

    def get_queryset(self):
        queryset = CertificateTemplate.objects.select_related('course')
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(course__instructors=self.request.user.lms_profile)


class CertificateTemplateCreateView(InstructorRequiredMixin, CreateView):
    model = CertificateTemplate
    form_class = CertificateTemplateForm
    template_name = 'lms/certificates/template_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.request.method in ('POST', 'PUT'):
            kwargs['files'] = self.request.FILES
        return kwargs

    def form_valid(self, form):
        course = form.cleaned_data['course']
        if not can_manage_course(self.request.user, course):
            messages.error(self.request, _("You cannot create certificate templates for this course."))
            return self.form_invalid(form)
        if self.request.POST.get('certificate_action') == 'draft':
            form.instance.status = 'draft'
        elif self.request.POST.get('certificate_action') == 'publish':
            CertificateTemplate.objects.filter(course=course, status='active').update(status='archived')
            form.instance.status = 'active'
        messages.success(self.request, _("Certificate template saved."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('lms:certificate_template_list')


class CertificateTemplateUpdateView(InstructorRequiredMixin, UpdateView):
    model = CertificateTemplate
    form_class = CertificateTemplateForm
    template_name = 'lms/certificates/template_form.html'

    def get_queryset(self):
        queryset = CertificateTemplate.objects.select_related('course')
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(course__instructors=self.request.user.lms_profile)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.request.method in ('POST', 'PUT'):
            kwargs['files'] = self.request.FILES
        return kwargs

    def form_valid(self, form):
        if self.request.POST.get('certificate_action') == 'draft':
            form.instance.status = 'draft'
        elif self.request.POST.get('certificate_action') == 'publish':
            CertificateTemplate.objects.filter(course=form.instance.course, status='active').exclude(pk=form.instance.pk).update(status='archived')
            form.instance.status = 'active'
        messages.success(self.request, _("Certificate template updated."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('lms:certificate_template_list')


class CertificateTemplatePreviewView(InstructorRequiredMixin, DetailView):
    model = CertificateTemplate
    template_name = 'lms/certificates/template_preview.html'
    context_object_name = 'template'

    def get_queryset(self):
        queryset = CertificateTemplate.objects.select_related('course')
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(course__instructors=self.request.user.lms_profile)


@login_required(login_url='login')
def publish_certificate_template(request, pk):
    template = get_object_or_404(CertificateTemplate, pk=pk)
    if not can_manage_course(request.user, template.course):
        messages.error(request, _("You cannot publish this certificate template."))
        return redirect('lms:certificate_template_list')
    CertificateTemplate.objects.filter(course=template.course, status='active').exclude(pk=template.pk).update(status='archived')
    template.status = 'active'
    template.save(update_fields=['status', 'updated_at'])
    messages.success(request, _("Certificate template published."))
    return redirect('lms:certificate_template_list')


def verify_certificate(request, certificate_id):
    certificate = get_object_or_404(
        StudentCertificate.objects.select_related('student', 'course', 'template'),
        certificate_id=certificate_id,
    )
    context = {
        'certificate': certificate,
        'student_legal_name': _resolve_student_name(certificate.student),
        'instructor_legal_name': _resolve_instructor_name(certificate.course, certificate.template),
    }
    return render(request, 'lms/certificates/verify.html', context)


@login_required(login_url='login')
@legal_name_required
def certificate_detail(request, certificate_id):
    """Beautiful 'Certificate ready' landing page before the actual download."""
    certificate = get_object_or_404(
        StudentCertificate.objects.select_related('student', 'course', 'template'),
        certificate_id=certificate_id,
    )
    is_owner = certificate.student_id == request.user.id
    if not is_owner and not can_manage_course(request.user, certificate.course):
        messages.error(request, _("You can only view certificates you earned."))
        return redirect('lms:student_dashboard')

    from .certificates import certificate_context
    from django.conf import settings as django_settings
    downloads_enabled = bool(getattr(django_settings, 'CERTIFICATE_DOWNLOADS_ENABLED', False))

    ctx = certificate_context(certificate, request=request)
    ctx.update({
        'is_owner': is_owner,
        'downloads_enabled': downloads_enabled,
        'download_url': reverse('lms:certificate_download', kwargs={'certificate_id': certificate.certificate_id}),
        'verify_url': ctx.get('verification_url'),
        'page_title': _("Your Certificate is Ready"),
        'certificate_previews': _certificate_previews_json([certificate]),
    })
    return render(request, 'lms/certificates/certificate_detail.html', ctx)


@login_required(login_url='login')
@legal_name_required
def download_certificate(request, certificate_id):
    from django.conf import settings as django_settings
    certificate = get_object_or_404(
        StudentCertificate.objects.select_related('student', 'course', 'template'),
        certificate_id=certificate_id,
    )
    if certificate.student != request.user and not can_manage_course(request.user, certificate.course):
        messages.error(request, _("You can only download certificates you earned."))
        return redirect('lms:student_dashboard')

    if not getattr(django_settings, 'CERTIFICATE_DOWNLOADS_ENABLED', False):
        messages.info(
            request,
            _("Certificate downloads are not available yet. You can still preview your certificate."),
        )
        return redirect('lms:certificate_detail', certificate_id=certificate.certificate_id)

    from .certificates import certificate_pdf_response
    return certificate_pdf_response(certificate, request=request)


@login_required(login_url='login')
def grade_students(request, course_slug):
    """Grade students for a course"""
    course = get_object_or_404(Course, slug=course_slug)
    
    # Check permissions
    if not is_admin(request.user) and not course.instructors.filter(id=request.user.lms_profile.id).exists():
        messages.error(request, _("You are not authorized to grade students for this course."))
        return redirect('lms:course_detail', slug=course_slug)
    
    # Get current semester
    current_semester = Semester.objects.filter(is_current_semester=True).first()
    if not current_semester:
        messages.error(request, _("No active semester found. Please set a current semester first."))
        return redirect('lms:course_detail', slug=course_slug)
    
    # Get enrolled students
    enrollments = CourseEnrollment.objects.filter(course=course)
    students = [enrollment.student for enrollment in enrollments]
    
    if request.method == 'POST':
        # Process grade submissions
        for student in students:
            # Check if grade exists
            grade, created = Grade.objects.get_or_create(
                student=student,
                course=course,
                semester=current_semester
            )
            
            # Update grade values
            grade.attendance = float(request.POST.get(f'attendance_{student.id}', 0))
            grade.assignment = float(request.POST.get(f'assignment_{student.id}', 0))
            grade.mid_exam = float(request.POST.get(f'mid_exam_{student.id}', 0))
            grade.final_exam = float(request.POST.get(f'final_exam_{student.id}', 0))
            grade.save()  # This will trigger calculation of total and grade
        
        messages.success(request, _("Grades saved successfully."))
        return redirect('lms:course_detail', slug=course_slug)
    
    # Get existing grades
    grades = {}
    for student in students:
        grade = Grade.objects.filter(
            student=student,
            course=course,
            semester=current_semester
        ).first()
        
        grades[student.id] = grade
    
    context = {
        'course': course,
        'students': students,
        'grades': grades,
        'semester': current_semester
    }
    
    return render(request, 'lms/grade_students.html', context)


@login_required(login_url='login')
def student_dashboard(request):
    """Dashboard for students"""
    # Check if user is a student
    if not hasattr(request.user, 'lms_profile') or not is_student(request.user):
        messages.error(request, _("You are not registered as a student."))
        return redirect('lms:lms_home')

    profile = request.user.lms_profile

    # Get current semester
    current_semester = Semester.objects.filter(is_current_semester=True).first()
    
    # Get enrolled courses
    enrollments = CourseEnrollment.objects.filter(student=profile)
    courses = [enrollment.course for enrollment in enrollments]
    
    # Get grades
    grades = Grade.objects.filter(student=profile)
    certificates = StudentCertificate.objects.filter(student=request.user).select_related('course')
    
    # Get upcoming quizzes
    upcoming_quizzes = Quiz.objects.filter(
        course__in=courses,
        draft=False,
        due_date__gt=timezone.now()
    ).order_by('due_date')[:5]
    
    # Get recent course activities
    recent_contents = CourseContent.objects.filter(
        module__course__in=courses
    ).order_by('-date_added')[:10]
    
    # Calculate progress for each course and auto-issue certificates for completed ones
    from .utils import calculate_course_progress, issue_certificate_if_eligible
    course_progress = {}
    for course in courses:
        progress = calculate_course_progress(course, profile)
        course_progress[course.id] = progress
        if progress.get('course_completed'):
            issue_certificate_if_eligible(course, profile)
    
    # Re-fetch certificates after any auto-issuance
    certificates = StudentCertificate.objects.filter(student=request.user).select_related('course', 'template', 'template__course')

    context = {
        'profile': profile,
        'current_semester': current_semester,
        'courses': courses,
        'grades': grades,
        'upcoming_quizzes': upcoming_quizzes,
        'recent_contents': recent_contents,
        'course_progress': course_progress,
        'certificates': certificates,
        'certificate_previews': _certificate_previews_json(certificates),
        'needs_legal_name': not profile.has_legal_name,
        'certificate_downloads_enabled': bool(getattr(settings, 'CERTIFICATE_DOWNLOADS_ENABLED', False)),
    }

    return render(request, 'lms/student_dashboard.html', context)


@login_required(login_url='login')
def instructor_dashboard(request):
    """Dashboard for instructors"""
    # Check if user is an instructor
    if not hasattr(request.user, 'lms_profile') or not is_instructor(request.user):
        messages.error(request, _("You are not registered as an instructor."))
        return redirect('lms:lms_home')
    
    profile = request.user.lms_profile
    
    # Get current semester
    current_semester = Semester.objects.filter(is_current_semester=True).first()
    
    # Get teaching courses
    teaching_courses = Course.objects.filter(instructors=profile)
    
    # Get student enrollments in instructor's courses
    enrollments = CourseEnrollment.objects.filter(course__in=teaching_courses)
    
    # Get recent quizzes
    recent_quizzes = Quiz.objects.filter(
        course__in=teaching_courses
    ).order_by('-timestamp')[:10]
    
    # Get quiz statistics
    quiz_stats = {}
    for course in teaching_courses:
        course_quizzes = Quiz.objects.filter(course=course)
        for quiz in course_quizzes:
            attempts = QuizTaker.objects.filter(quiz=quiz, completed=True)
            avg_score = attempts.aggregate(Avg('score'))['score__avg'] or 0
            quiz_stats[quiz.id] = {
                'attempts': attempts.count(),
                'avg_score': avg_score
            }
    
    # Calculate student progress for each course
    from .utils import get_all_enrolled_students_progress
    courses_student_progress = {}
    for course in teaching_courses:
        courses_student_progress[course.id] = get_all_enrolled_students_progress(course)
    
    # Calculate course completion statistics
    course_completion_stats = {}
    for course in teaching_courses:
        if course.id in courses_student_progress:
            progress_data = courses_student_progress[course.id]
            if progress_data:
                completion_rates = [data['progress']['percentage'] for data in progress_data.values()]
                if completion_rates:
                    avg_completion = sum(completion_rates) / len(completion_rates)
                    course_completion_stats[course.id] = {
                        'avg_completion': round(avg_completion, 1),
                        'student_count': len(completion_rates),
                        'completed_25': len([r for r in completion_rates if r >= 25]),
                        'completed_50': len([r for r in completion_rates if r >= 50]),
                        'completed_75': len([r for r in completion_rates if r >= 75]),
                        'completed_100': len([r for r in completion_rates if r >= 100])
                    }
    
    # Calculate the total number of students
    total_students = len(set(enrollment.student.id for enrollment in enrollments))
    
    # Count active quizzes
    active_quizzes = Quiz.objects.filter(
        course__in=teaching_courses,
        draft=False,
        due_date__gt=timezone.now()
    ).count()
    
    # Count incomplete courses (less than 70% of modules have content)
    incomplete_courses = 0
    for course in teaching_courses:
        modules = course.modules.all()
        if modules:
            empty_modules = modules.annotate(content_count=Count('contents')).filter(content_count=0).count()
            if empty_modules / modules.count() > 0.3:  # More than 30% of modules are empty
                incomplete_courses += 1
    
    # Get instructor's payment methods
    payment_methods = PaymentMethod.objects.filter(instructor=profile)

    context = {
        'profile': profile,
        'current_semester': current_semester,
        'teaching_courses': teaching_courses,
        'enrollments': enrollments,
        'recent_quizzes': recent_quizzes,
        'quiz_stats': quiz_stats,
        'courses_student_progress': courses_student_progress,
        'course_completion_stats': course_completion_stats,
        'total_students': total_students,
        'active_quizzes': active_quizzes,
        'incomplete_courses': incomplete_courses,
        'payment_methods': payment_methods,
        'needs_legal_name': not profile.has_legal_name,
    }

    return render(request, 'lms/instructor_dashboard.html', context)


@login_required(login_url='login')
def request_instructor_role(request):
    """View for users to request instructor status"""
    # Check if user already has a pending or approved request
    existing_request = InstructorRequest.objects.filter(
        user=request.user, 
        status__in=['pending', 'approved']
    ).first()
    
    if existing_request:
        if existing_request.status == 'approved':
            messages.info(request, _("Your request to become an instructor has already been approved."))
            return redirect('lms:lms_home')
        else:
            messages.info(request, _("You already have a pending instructor request."))
            return redirect('lms:instructor_request_status')
    
    # Check if user is already an instructor
    if hasattr(request.user, 'lms_profile') and request.user.lms_profile.role == 'instructor':
        messages.info(request, _("You are already registered as an instructor."))
        return redirect('lms:instructor_dashboard')
    
    if request.method == 'POST':
        form = InstructorRequestForm(request.POST, request.FILES)
        if form.is_valid():
            instructor_request = form.save(commit=False)
            instructor_request.user = request.user
            instructor_request.save()
            
            # Log the activity
            ActivityLog.objects.create(
                message=_(f"User {request.user.username} submitted an instructor request.")
            )
            
            messages.success(request, _("Your instructor request has been submitted successfully and is pending review."))
            return redirect('lms:instructor_request_status')
    else:
        form = InstructorRequestForm()
    
    context = {
        'form': form
    }
    
    return render(request, 'lms/instructor_request_form.html', context)


@login_required(login_url='login')
def instructor_request_status(request):
    """View for users to check their instructor request status"""
    instructor_request = InstructorRequest.objects.filter(user=request.user).order_by('-created_at').first()
    
    if not instructor_request:
        messages.info(request, _("You haven't submitted an instructor request yet."))
        return redirect('lms:request_instructor_role')
    
    context = {
        'instructor_request': instructor_request
    }
    
    return render(request, 'lms/instructor_request_status.html', context)


@login_required
def session_keep_alive(request):
    """
    Simple view to keep a user's session alive
    This should be called via AJAX periodically while the user is active
    """
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        raise Http404("This endpoint is for AJAX requests only")
        
    # Update the last activity timestamp
    request.session['last_activity'] = time.time()
    
    # Return a simple OK response
    return JsonResponse({"status": "ok"})

# Debug file upload view
def debug_upload_view(request):
    """
    Debug view for testing file uploads.
    This is a temporary view for troubleshooting file upload issues.
    """
    from django.conf import settings

    if not settings.DEBUG:
        raise Http404("Not found")

    if request.method == 'POST':
        print(f"DEBUG UPLOAD: Files in request: {request.FILES}")
        if 'test_file' in request.FILES:
            file = request.FILES['test_file']
            print(f"DEBUG UPLOAD: File name: {file.name}")
            print(f"DEBUG UPLOAD: File size: {file.size}")
            print(f"DEBUG UPLOAD: File content type: {file.content_type}")
            
            # Save the file using a generated filename to avoid path manipulation.
            import os
            from pathlib import Path
            from uuid import uuid4
            from django.core.files.storage import default_storage

            suffix = Path(file.name).suffix.lower()
            safe_name = f"{uuid4().hex}{suffix}"
            relative_path = os.path.join('lms', 'debug_uploads', safe_name)
            saved_path = default_storage.save(relative_path, file)
            file_path = default_storage.path(saved_path)
                    
            return render(request, 'lms/debug_upload.html', {
                'success': True,
                'file_name': file.name,
                'file_path': file_path
            })
    
    return render(request, 'lms/debug_upload.html')

@login_required
@staff_member_required
def toggle_ad_exemption(request, user_id):
    """
    Toggle ad exemption for a specific user
    Only staff members can access this view
    """
    user = get_object_or_404(User, id=user_id)
    
    try:
        # If exemption exists, delete it
        exemption = AdExemptUser.objects.get(user=user)
        exemption.delete()
        messages.success(request, f"Ad exemption for {user.username} has been removed.")
    except AdExemptUser.DoesNotExist:
        # If exemption doesn't exist, create it
        reason = request.GET.get('reason', 'Staff exemption')
        AdExemptUser.objects.create(user=user, reason=reason)
        messages.success(request, f"Ad exemption for {user.username} has been added.")
    
    # Redirect to the user's admin page
    return redirect(f'/admin/auth/user/{user.id}/change/')


@login_required(login_url='login')
def payment_form(request, slug):
    """View for submitting payment proof for a premium course"""
    course = get_object_or_404(Course, slug=slug)
    
    # Redirect if course is free
    if course.is_free:
        messages.warning(request, _("This is a free course and does not require payment."))
        return redirect('lms:course_detail', slug=course.slug)
    
    # Get user's profile
    if not hasattr(request.user, 'lms_profile'):
        profile = LMSProfile.objects.create(user=request.user, role='student')
    else:
        profile = request.user.lms_profile
    
    # Try to get enrollment
    enrollment = CourseEnrollment.objects.filter(student=profile, course=course).first()
    # Don't allow payment if already approved
    if enrollment and enrollment.payment_status == 'approved':
        messages.info(request, _("Your payment for this course has already been approved."))
        return redirect('lms:course_detail', slug=course.slug)

    # Show only payment methods for the course's instructor(s)
    instructors = course.instructors.all()
    payment_methods = PaymentMethod.objects.filter(is_active=True, instructor__in=instructors)

    if request.method == 'POST':
        payment_method_id = request.POST.get('payment_method')
        payment_proof = request.FILES.get('payment_proof')
        payment_notes = request.POST.get('payment_notes', '')

        if not payment_proof:
            messages.error(request, _("Please upload a payment proof image."))
        elif not payment_method_id:
            messages.error(request, _("Please select a payment method."))
        else:
            try:
                payment_method = PaymentMethod.objects.get(id=payment_method_id)
                # If not enrolled, create enrollment now
                if not enrollment:
                    enrollment = CourseEnrollment.objects.create(
                        student=profile,
                        course=course,
                        payment_status='pending',
                        payment_method=payment_method,
                        payment_proof=payment_proof,
                        payment_notes=payment_notes,
                        payment_date=timezone.now(),
                    )
                else:
                    enrollment.payment_method = payment_method
                    enrollment.payment_proof = payment_proof
                    enrollment.payment_notes = payment_notes
                    enrollment.payment_date = timezone.now()
                    enrollment.payment_status = 'pending'
                    enrollment.save()
                # Log activity
                ActivityLog.objects.create(
                    message=_(f"User {request.user.username} submitted payment proof for {course.title}.")
                )
                messages.success(request, _("Your payment proof has been submitted and is awaiting approval."))
                return redirect('lms:payment_pending', slug=course.slug)
            except PaymentMethod.DoesNotExist:
                messages.error(request, _("Invalid payment method selected."))

    return render(request, 'lms/payment_form.html', {
        'course': course,
        'enrollment': enrollment,
        'payment_methods': payment_methods,
    })


@login_required(login_url='login')
def payment_pending(request, slug):
    """View for showing payment pending status"""
    course = get_object_or_404(Course, slug=slug)
    
    # Get user's profile
    if not hasattr(request.user, 'lms_profile'):
        return redirect('lms:course_detail', slug=course.slug)
    
    profile = request.user.lms_profile
    
    # Get enrollment
    try:
        enrollment = CourseEnrollment.objects.get(student=profile, course=course)
    except CourseEnrollment.DoesNotExist:
        return redirect('lms:course_detail', slug=course.slug)
    
    # Redirect if payment is not pending
    if enrollment.payment_status == 'approved':
        messages.success(request, _("Your payment has been approved! You now have full access to the course."))
        return redirect('lms:course_detail', slug=course.slug)
    elif enrollment.payment_status == 'rejected':
        messages.error(request, _("Your payment was rejected. Please submit a new payment proof."))
        return redirect('lms:payment_form', slug=course.slug)
    elif enrollment.payment_status == 'not_required':
        return redirect('lms:course_detail', slug=course.slug)
    
    # Show pending page for pending status
    user_role = profile.role if hasattr(profile, 'role') else 'student'
    return render(request, 'lms/payment_pending.html', {
        'course': course,
        'enrollment': enrollment,
        'user_role': user_role,
    })
