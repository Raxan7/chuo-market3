"""
Views for the LMS application
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, TemplateView, View
)
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    LMSProfile, Program, Course, CourseModule, CourseContent, Quiz, Question,
    MCQuestion, Choice, TF_Question, Essay_Question, QuizTaker, StudentAnswer, ContentAccess,
    Grade, Semester, CourseEnrollment, ActivityLog, InstructorRequest
)
from .forms import (
    LMSProfileForm, CourseForm, CourseModuleForm, CourseContentForm,
    QuizForm, MCQuestionForm, ChoiceForm, TFQuestionForm, EssayQuestionForm,
    GradeForm, CourseEnrollForm, EssayAnswerForm, InstructorRequestForm,
    ProgramForm
)


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


@login_required(login_url='login')
def lms_home(request):
    """LMS home page view"""
    
    # Create profile if it doesn't exist
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
        'current_semester': current_semester
    }
    
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
        context['courses'] = Course.objects.filter(program=program)
        return context


class CourseListView(ListView):
    """List all courses"""
    model = Course
    template_name = 'lms/course_list.html'
    context_object_name = 'courses'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Course.objects.all()
        
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
        context['current_filters'] = {
            'semester': self.request.GET.get('semester', ''),
            'program': self.request.GET.get('program', ''),
            'level': self.request.GET.get('level', ''),
            'course_type': self.request.GET.get('course_type', ''),
            'q': self.request.GET.get('q', ''),
        }
        return context


class CourseDetailView(DetailView):
    """Show details of a course"""
    model = Course
    template_name = 'lms/course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        
        # Get course modules with contents
        modules = CourseModule.objects.filter(course=course).prefetch_related('contents')
        
        # Get quizzes for this course
        quizzes = Quiz.objects.filter(course=course)
        
        # Check if user is enrolled
        is_enrolled = False
        student_profile = None
        if self.request.user.is_authenticated and hasattr(self.request.user, 'lms_profile'):
            student_profile = self.request.user.lms_profile
            is_enrolled = CourseEnrollment.objects.filter(
                student=student_profile,
                course=course
            ).exists()
        
        # Check if user is instructor for this course
        is_course_instructor = False
        if self.request.user.is_authenticated and hasattr(self.request.user, 'lms_profile'):
            is_course_instructor = course.instructors.filter(id=self.request.user.lms_profile.id).exists()
        
        # Get course progress if user is enrolled
        course_progress = None
        if is_enrolled and student_profile:
            from .utils import calculate_course_progress
            course_progress = calculate_course_progress(course, student_profile)
            
        # Add is_free status to context
        context['is_free'] = course.is_free
        
        # If user is instructor, get progress data for all enrolled students
        students_progress = None
        if is_course_instructor:
            from .utils import get_all_enrolled_students_progress
            students_progress = get_all_enrolled_students_progress(course)
        
        context.update({
            'modules': modules,
            'quizzes': quizzes,
            'is_enrolled': is_enrolled,
            'is_course_instructor': is_course_instructor,
            'course_progress': course_progress,
            'students_progress': students_progress,
        })
        
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
    if CourseEnrollment.objects.filter(student=profile, course=course).exists():
        messages.info(request, _("You are already enrolled in this course."))
        return redirect('lms:course_detail', slug=course.slug)
    
    # Create enrollment
    CourseEnrollment.objects.create(student=profile, course=course)
    
    # Log activity
    ActivityLog.objects.create(
        message=_(f"User {request.user.username} enrolled in course {course.title}.")
    )
    
    messages.success(request, _(f"You have successfully enrolled in {course.title}."))
    return redirect('lms:course_detail', slug=course.slug)


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
    """Show details of a quiz"""
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
                # Check single attempt restriction
                if quiz.single_attempt and completed_attempt:
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
            'has_already_taken': completed_attempt is not None,
            'user_score': user_score,
            'is_past_due': is_past_due,
            'past_due': is_past_due,
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
    
    # Check single attempt restriction
    if quiz.single_attempt:
        completed_attempts = QuizTaker.objects.filter(
            user=profile,
            quiz=quiz,
            completed=True
        )
        
        if completed_attempts.exists():
            messages.error(request, _("You have already completed this quiz and can only take it once."))
            return redirect('lms:quiz_detail', slug=quiz.slug)
    
    # Check if quiz is past due date
    if quiz.due_date and timezone.now() > quiz.due_date:
        messages.error(request, _("This quiz is past its due date."))
        return redirect('lms:quiz_detail', slug=quiz.slug)
    
    # Create new quiz taker instance or get existing incomplete one
    quiz_taker, created = QuizTaker.objects.get_or_create(
        user=profile,
        quiz=quiz,
        completed=False
    )
    
    if created:
        # Reset the start time for a new attempt
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
    question = questions[question_number - 1]
    
    # Handle form submission
    if request.method == 'POST':
        # Process different question types
        if isinstance(question, MCQuestion):
            # Handle multiple choice
            selected_choice_id = request.POST.get('choice')
            if selected_choice_id:
                selected_choice = get_object_or_404(Choice, id=selected_choice_id)
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
            answer = request.POST.get('answer')
            if answer in ['true', 'false']:
                selected_answer = answer == 'true'
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
                        'is_correct': None  # Essay questions need manual grading
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
    
    # Create activity log
    ActivityLog.objects.create(
        message=_(f"User {request.user.username} completed quiz '{quiz.title}' with score {score_percentage:.1f}%.")
    )
    
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
    
    context = {
        'quiz_taker': quiz_taker,
        'quiz': quiz,
        'answers': answers,
        'passed': passed,
        'show_answers': quiz.answers_at_end or not quiz.exam_paper
    }
    
    return render(request, 'lms/quiz_results.html', context)


@login_required(login_url='login')
def course_content_detail(request, course_slug, content_id):
    """Show course content details"""
    course = get_object_or_404(Course, slug=course_slug)
    content = get_object_or_404(CourseContent, id=content_id, module__course=course)
    
    # Check if user is enrolled or is instructor
    is_enrolled = False
    is_instructor = False
    
    if hasattr(request.user, 'lms_profile'):
        profile = request.user.lms_profile
        is_enrolled = CourseEnrollment.objects.filter(student=profile, course=course).exists()
        is_instructor = course.instructors.filter(id=profile.id).exists()
    
    if not (is_enrolled or is_instructor or request.user.is_staff):
        messages.error(request, _("You must be enrolled in this course to view its content."))
        return redirect('lms:course_detail', slug=course.slug)
    
    # Track content access for students (not instructors or staff)
    if is_enrolled and not is_instructor and not request.user.is_staff:
        content_access, created = ContentAccess.objects.get_or_create(
            student=profile,
            content=content
        )
        
        # Mark as completed if it's a request from the "mark complete" button
        if request.GET.get('mark_complete') == 'true':
            content_access.mark_complete()
            messages.success(request, _("Content marked as completed!"))
            return redirect('lms:content_detail', course_slug=course_slug, content_id=content_id)
    
    # Check if this content is completed by the student
    content_completed = False
    if hasattr(request.user, 'lms_profile') and is_enrolled:
        content_completed = ContentAccess.objects.filter(
            student=profile,
            content=content,
            completed=True
        ).exists()
    
    context = {
        'course': course,
        'content': content,
        'module': content.module,
        'content_completed': content_completed
    }
    
    return render(request, 'lms/course_content_detail.html', context)


class CourseCreateView(InstructorRequiredMixin, CreateView):
    """Create a new course"""
    model = Course
    form_class = CourseForm
    template_name = 'lms/course_form.html'
    
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
        return super().post(request, *args, **kwargs)
    
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
    """Create a new quiz"""
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
        
        return super().dispatch(request, *args, **kwargs)
    
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
    """Add a multiple choice question to a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check permissions
    if not is_admin(request.user) and not quiz.course.instructors.filter(id=request.user.lms_profile.id).exists():
        messages.error(request, _("You are not authorized to add questions to this quiz."))
        return redirect('lms:quiz_detail', slug=quiz.slug)
    
    if request.method == 'POST':
        form = MCQuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            
            # Get choices
            num_choices = int(request.POST.get('num_choices', 4))
            for i in range(num_choices):
                content = request.POST.get(f'choice_{i}_content', '')
                correct = request.POST.get(f'choice_{i}_correct', '') == 'on'
                
                if content.strip():
                    Choice.objects.create(
                        question=question,
                        content=content,
                        correct=correct
                    )
            
            messages.success(request, _("Multiple choice question added successfully."))
            return redirect('lms:quiz_detail', slug=quiz.slug)
    else:
        form = MCQuestionForm()
    
    context = {
        'form': form,
        'quiz': quiz,
        'question_type': 'MC'
    }
    
    return render(request, 'lms/mc_question_form.html', context)


@login_required(login_url='login')
def add_tf_question(request, quiz_id):
    """Add a true/false question to a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check permissions
    if not is_admin(request.user) and not quiz.course.instructors.filter(id=request.user.lms_profile.id).exists():
        messages.error(request, _("You are not authorized to add questions to this quiz."))
        return redirect('lms:quiz_detail', slug=quiz.slug)
    
    if request.method == 'POST':
        form = TFQuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            
            messages.success(request, _("True/False question added successfully."))
            return redirect('lms:quiz_detail', slug=quiz.slug)
    else:
        form = TFQuestionForm()
    
    context = {
        'form': form,
        'quiz': quiz,
        'question_type': 'TF'
    }
    
    return render(request, 'lms/tf_question_form.html', context)


@login_required(login_url='login')
def add_essay_question(request, quiz_id):
    """Add an essay question to a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
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
    
    # Calculate progress for each course
    from .utils import calculate_course_progress
    course_progress = {}
    for course in courses:
        course_progress[course.id] = calculate_course_progress(course, profile)
    
    context = {
        'profile': profile,
        'current_semester': current_semester,
        'courses': courses,
        'grades': grades,
        'upcoming_quizzes': upcoming_quizzes,
        'recent_contents': recent_contents,
        'course_progress': course_progress
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
        'incomplete_courses': incomplete_courses
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


class CourseAdvertisementView(View):
    """
    Display an advertisement before redirecting to the course detail page
    
    This view checks site settings to determine whether to show ads,
    and only shows ads for free courses when the setting is enabled.
    """
    def get(self, request, *args, **kwargs):
        course_slug = kwargs.get('slug')
        course = get_object_or_404(Course, slug=course_slug)
        
        # Check if ads are enabled for free courses in site settings
        from .models import SiteSettings
        settings = SiteSettings.get_settings()
        show_ads = settings.show_ads_before_free_courses and course.is_free
        
        # Skip the ad page if ads are disabled or the course is not free
        if not show_ads:
            # Redirect directly to the course detail page
            return redirect('lms:course_detail_direct', slug=course_slug)
            
        # Generate the URL for the course detail page
        course_detail_url = reverse('lms:course_detail_direct', kwargs={'slug': course_slug})
        
        context = {
            'course': course,
            'course_detail_url': course_detail_url,
            'show_ads': show_ads,
        }
        
        return render(request, 'lms/course_ad.html', context)
