"""
Models for the LMS application, based on SkyLearn but adapted for chuo-market3
"""
from django.db import models
from django.urls import reverse
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
import random
import string
import uuid
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete

# Constants for choices
LEVEL_CHOICES = (
    ('1', _('Level 1')),
    ('2', _('Level 2')),
    ('3', _('Level 3')),
    ('4', _('Level 4')),
    ('5', _('Level 5')),
    ('6', _('Level 6')),
)

SEMESTER_CHOICES = (
    ('First', _('First')),
    ('Second', _('Second')),
)

YEARS = (
    (1, _('First')),
    (2, _('Second')),
    (3, _('Third')),
    (4, _('Fourth')),
    (5, _('Fifth')),
    (6, _('Sixth')),
)

CATEGORY_OPTIONS = (
    ('assignment', _('Assignment')),
    ('exam', _('Exam')),
    ('practice', _('Practice Quiz')),
)

CHOICE_ORDER_OPTIONS = (
    ('content', _('Content')),
    ('random', _('Random')),
    ('none', _('None')),
)

ESSAY_ANSWER_TYPES = (
    ('text', _('Text')),
    ('file_upload', _('File Upload')),
    ('both', _('Both')),
)


class ActivityLog(models.Model):
    """
    Model to store activity logs in the LMS
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.timestamp}: {self.message}"


class Semester(models.Model):
    """
    Model to represent a semester
    """
    year = models.IntegerField(choices=YEARS, default=1)
    semester = models.CharField(choices=SEMESTER_CHOICES, max_length=10, default='First')
    is_current_semester = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.get_semester_display()} Semester - Year {self.get_year_display()}"
    
    class Meta:
        unique_together = ['semester', 'year']


class LMSProfile(models.Model):
    """
    Extended profile for LMS users
    """
    ROLE_CHOICES = (
        ('student', _('Student')),
        ('instructor', _('Instructor')),
        ('admin', _('Administrator')),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lms_profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='lms/profile_pictures/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Full legal name as it should appear on certificates."),
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def display_legal_name(self):
        return (self.legal_name or '').strip()

    @property
    def has_legal_name(self):
        return bool((self.legal_name or '').strip())


class Program(models.Model):
    """
    Educational program (e.g., Computer Science, Business Administration)
    """
    title = models.CharField(max_length=150, unique=True)
    summary = models.TextField(blank=True)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse("lms:program_detail", kwargs={"pk": self.pk})


class Course(models.Model):
    """
    Course model representing a single course in the LMS
    """
    COURSE_TYPE_CHOICES = (
        ('university', _('University Course')),
        ('general', _('General Course')),
    )
    
    course_type = models.CharField(
        max_length=10, 
        choices=COURSE_TYPE_CHOICES, 
        default='university',
        help_text=_("University courses require academic fields like course code, program, etc.")
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, max_length=100)
    summary = models.TextField(blank=True, default='', help_text=_("Brief summary of the course"))
    content = models.TextField(blank=True, default='', help_text=_("Detailed course description and content"))
    is_free = models.BooleanField(default=True, help_text=_("Whether this course is free or paid"))
    image = models.ImageField(upload_to='lms/course_images/', blank=True, null=True)
    instructors = models.ManyToManyField(LMSProfile, related_name='courses_teaching',
                                        limit_choices_to={'role': 'instructor'})
    students = models.ManyToManyField(LMSProfile, through='CourseEnrollment', 
                                     related_name='courses_enrolled')
    
    # Fields specific to university courses (nullable for general courses)
    code = models.CharField(max_length=20, unique=True, null=True, blank=True,
                          help_text=_("Required for university courses only"))
    credit = models.IntegerField(default=3, null=True, blank=True,
                               help_text=_("Required for university courses only"))
    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True, blank=True,
                              help_text=_("Required for university courses only"))
    level = models.CharField(max_length=2, choices=LEVEL_CHOICES, null=True, blank=True,
                          help_text=_("Required for university courses only"))
    year = models.IntegerField(choices=YEARS, default=1, null=True, blank=True,
                             help_text=_("Required for university courses only"))
    semester = models.CharField(choices=SEMESTER_CHOICES, max_length=10, null=True, blank=True,
                             help_text=_("Required for university courses only"))
    is_elective = models.BooleanField(default=False, help_text=_("Applies to university courses only"))
    is_pinned = models.BooleanField(default=False, help_text=_("Pin this course at the top of listings"))
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text=_('Price for paid course'))
    
    def __str__(self):
        if self.course_type == 'university' and self.code:
            return f"{self.title} ({self.code})"
        return self.title
    
    def get_absolute_url(self):
        return reverse("lms:course_detail", kwargs={"slug": self.slug})
        
    def get_direct_url(self):
        """Get URL that bypasses the advertisement"""
        return reverse("lms:course_detail_direct", kwargs={"slug": self.slug})
    
    @property
    def is_current_semester(self):
        current_semester = Semester.objects.filter(is_current_semester=True).first()
        return self.semester == current_semester.semester if current_semester else False
        
    def user_has_access(self, user):
        """
        Check if the user has access to this course
        """
        if self.is_free:
            return True
            
        if not user.is_authenticated:
            return False
            
        try:
            enrollment = CourseEnrollment.objects.get(
                student__user=user, 
                course=self
            )
            return enrollment.payment_status == 'approved'
        except CourseEnrollment.DoesNotExist:
            return False


class PaymentMethod(models.Model):
    """
    Stores payment method information like lipa number
    """
    name = models.CharField(max_length=100)
    instructor = models.ForeignKey('LMSProfile', on_delete=models.CASCADE, related_name='payment_methods', help_text="Instructor who accepts this payment method", null=True, blank=True)
    payment_number = models.CharField(max_length=100, help_text="Payment number or account (e.g. phone number, bank account)", null=False, blank=True, default='N/A')
    instructions = models.TextField(blank=True)
    image = models.ImageField(upload_to='lms/payment_methods/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.payment_number}) - {self.instructor.user.username}"


class CourseEnrollment(models.Model):
    """
    Represents a student's enrollment in a course
    """
    PAYMENT_STATUS_CHOICES = (
        ('not_required', _('Not Required')),
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    )
    
    student = models.ForeignKey(LMSProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateTimeField(auto_now_add=True)
    
    # Payment related fields
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='not_required',
        help_text=_("Payment status for premium courses")
    )
    payment_proof = models.ImageField(
        upload_to='lms/payment_proofs/', 
        blank=True, 
        null=True,
        help_text=_("Upload proof of payment for premium courses")
    )
    payment_date = models.DateTimeField(blank=True, null=True)
    payment_method = models.ForeignKey(
        PaymentMethod, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
        help_text=_("Payment method used")
    )
    payment_approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='approved_enrollments',
        help_text=_("Admin who approved the payment")
    )
    payment_approved_date = models.DateTimeField(blank=True, null=True)
    payment_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['student', 'course']
    
    def __str__(self):
        return f"{self.student.user.username} enrolled in {self.course.title}"
    
    @property
    def has_access(self):
        """Determine if student has access to the course"""
        if self.course.is_free:
            return True
        return self.payment_status == 'approved'
        
    def save(self, *args, **kwargs):
        # For free courses, automatically set payment_status to not_required
        if self.course.is_free and self.payment_status == 'pending':
            self.payment_status = 'not_required'
        
        # If payment proof is uploaded, update status to pending
        if self.payment_proof and self.payment_status == 'not_required' and not self.course.is_free:
            self.payment_status = 'pending'
            self.payment_date = timezone.now()
            
        super().save(*args, **kwargs)


class CourseModule(models.Model):
    """
    A module within a course (chapter or section)
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    order = models.PositiveIntegerField(default=0)
    skip_assessment = models.BooleanField(
        default=False,
        verbose_name=_("Skip Assessment"),
        help_text=_("Mark this module as an overview or introduction module without a quiz.")
    )
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.title} - {self.course.title}"

    @property
    def requires_assessment(self):
        return not self.skip_assessment

    def get_previous_module(self):
        return CourseModule.objects.filter(
            models.Q(course=self.course) & (
                models.Q(order__lt=self.order) | 
                models.Q(order=self.order, id__lt=self.id)
            )
        ).order_by('-order', '-id').first()

    def get_next_module(self):
        return CourseModule.objects.filter(
            models.Q(course=self.course) & (
                models.Q(order__gt=self.order) | 
                models.Q(order=self.order, id__gt=self.id)
            )
        ).order_by('order', 'id').first()

    def get_progress_for(self, student):
        if not student:
            return None
        return self.student_progress.filter(student=student).first()

    def is_unlocked_for(self, student):
        if not student:
            return False

        previous_module = self.get_previous_module()
        if previous_module is None:
            return True

        previous_progress = previous_module.get_progress_for(student)
        if not previous_progress:
            return False

        return previous_progress.unlocks_next

    def is_locked_for(self, student):
        return not self.is_unlocked_for(student)

    def lock_message_for(self, student):
        previous_module = self.get_previous_module()
        if previous_module is None:
            return ''

        if getattr(previous_module, 'skip_assessment', False):
            return _(
                "Complete %(module)s to unlock this module."
            ) % {'module': previous_module.title}

        return _(
            "Complete %(module)s and pass its quiz with at least %(score)s%% to unlock this module."
        ) % {
            'module': previous_module.title,
            'score': ModuleProgress.PASSING_PERCENTAGE,
        }


class CourseContent(models.Model):
    """
    Content items within a course module
    """
    CONTENT_TYPES = (
        ('document', _('Document')),
        ('video', _('Video')),
        ('link', _('External Link')),
        ('text', _('Text Content')),
    )
    
    title = models.CharField(max_length=200)
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    document = models.FileField(
        upload_to='lms/course_documents/',
        blank=True, 
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt'])
        ]
    )
    video_url = models.URLField(blank=True, null=True)
    external_link = models.URLField(blank=True, null=True)
    text_content = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("lms:content_detail", kwargs={
            "course_slug": self.module.course.slug,
            "content_id": self.id,
        })


class ContentAccess(models.Model):
    """
    Tracks when a student accesses course content
    """
    student = models.ForeignKey(LMSProfile, on_delete=models.CASCADE)
    content = models.ForeignKey(CourseContent, on_delete=models.CASCADE)
    accessed_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['student', 'content']
        ordering = ['-accessed_at']
    
    def __str__(self):
        return f"{self.student.user.username} accessed {self.content.title}"

    def mark_complete(self):
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save()


class Quiz(models.Model):
    """
    Quiz model for assessments
    """
    GENERATION_STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('ready', _('Ready')),
        ('failed', _('Failed')),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(verbose_name=_("Title"), max_length=60)
    slug = models.SlugField(unique=True, blank=True, max_length=150)
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        help_text=_("A detailed description of the quiz")
    )
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    generated_for = models.ForeignKey(
        LMSProfile,
        on_delete=models.CASCADE,
        related_name='generated_quizzes',
        null=True,
        blank=True,
        help_text=_("When set, this quiz is personalized for one enrolled learner.")
    )
    category = models.CharField(max_length=20, choices=CATEGORY_OPTIONS, blank=True)
    random_order = models.BooleanField(
        default=False,
        verbose_name=_("Random Order"),
        help_text=_("Display the questions in a random order or as they are set?")
    )
    answers_at_end = models.BooleanField(
        default=False,
        verbose_name=_("Answers at end"),
        help_text=_("Correct answer is NOT shown after question. Answers displayed at the end.")
    )
    exam_paper = models.BooleanField(
        default=False,
        verbose_name=_("Exam Paper"),
        help_text=_(
            "If yes, the result of each attempt by a user will be stored. Necessary for marking."
        )
    )
    single_attempt = models.BooleanField(
        default=False,
        verbose_name=_("Single Attempt"),
        help_text=_("If yes, only one attempt by a user will be permitted.")
    )
    pass_mark = models.SmallIntegerField(
        default=70,
        verbose_name=_("Pass Mark"),
        validators=[MaxValueValidator(100)],
        help_text=_("Percentage required to pass exam.")
    )
    draft = models.BooleanField(
        default=False,
        verbose_name=_("Draft"),
        help_text=_(
            "If yes, the quiz is not displayed in the quiz list and can only be taken by users who can edit quizzes."
        )
    )
    due_date = models.DateTimeField(blank=True, null=True)
    generation_status = models.CharField(
        max_length=20,
        choices=GENERATION_STATUS_CHOICES,
        default='ready',
        help_text=_("Tracks whether a personalized assessment is being prepared.")
    )
    generation_message = models.TextField(blank=True, default='')
    generation_started_at = models.DateTimeField(blank=True, null=True)
    generation_completed_at = models.DateTimeField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")
        ordering = ['course', 'title']
        constraints = [
            models.UniqueConstraint(
                fields=['module', 'generated_for'],
                condition=Q(module__isnull=False, generated_for__isnull=False, draft=False),
                name='unique_personal_ai_quiz_per_module_student',
            ),
            models.UniqueConstraint(
                fields=['module'],
                condition=Q(module__isnull=False, generated_for__isnull=True, draft=False),
                name='unique_shared_ai_quiz_per_module',
            ),
        ]
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or 'quiz'
            suffix_parts = [base_slug]
            if self.module_id:
                suffix_parts.append(str(self.module_id))
            if self.generated_for_id:
                suffix_parts.append(str(self.generated_for_id))
            suffix_parts.append(uuid.uuid4().hex[:8])
            max_len = self._meta.get_field('slug').max_length or 150
            self.slug = slugify('-'.join(suffix_parts))[:max_len]

        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse("lms:quiz_detail", kwargs={"slug": self.slug})

    @property
    def get_questions(self):
        return self.questions.all()

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def total_points(self):
        return self.question_count

    @property
    def passing_score(self):
        return self.pass_mark

    @property
    def time_limit_mins(self):
        return 0

    @property
    def allowed_attempts(self):
        return 1 if self.single_attempt else 0


class Question(models.Model):
    """
    Base class for all question types
    """
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    figure = models.ImageField(upload_to='lms/quiz_figures', blank=True, null=True)
    content = models.TextField(help_text=_("Enter the question text"))
    explanation = models.TextField(
        blank=True,
        help_text=_("Explanation to be shown after the question has been answered.")
    )
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return self.content


class MCQuestion(Question):
    """
    Multiple Choice Question
    """
    choice_order = models.CharField(
        max_length=30, null=True, blank=True,
        choices=CHOICE_ORDER_OPTIONS,
        help_text=_("The order in which multichoice choice options are displayed")
    )
    
    def check_if_correct(self, selected_choice):
        return selected_choice.correct


class Choice(models.Model):
    """
    Choice for a multiple choice question
    """
    question = models.ForeignKey(MCQuestion, on_delete=models.CASCADE, related_name='choices')
    content = models.TextField(help_text=_("Enter the choice text that you want displayed"))
    correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.content


class TF_Question(Question):
    """
    True/False Question
    """
    correct = models.BooleanField(default=False)
    
    def check_if_correct(self, selected_choice):
        return selected_choice == self.correct


class Essay_Question(Question):
    """
    Essay style question with text answer or file upload
    """
    answer_type = models.CharField(
        max_length=20,
        choices=ESSAY_ANSWER_TYPES,
        default='text'
    )


class QuizTaker(models.Model):
    """
    Quiz attempt by a user
    """
    user = models.ForeignKey(LMSProfile, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completed = models.BooleanField(default=False)
    date_started = models.DateTimeField(auto_now_add=True)
    date_completed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'quiz']
        
    def __str__(self):
        return f"{self.user.user.username}: {self.quiz.title}"

    def get_score_percentage(self):
        return round(float(self.score or 0), 1)

    @property
    def passed(self):
        return self.completed and self.score >= self.quiz.pass_mark


class ModuleProgress(models.Model):
    """
    Stores a student's gate status for one course module.

    A module is complete only after all its content is marked complete and the
    module assessment has been passed at or above the required threshold.
    """
    PASSING_PERCENTAGE = 70

    student = models.ForeignKey(LMSProfile, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='student_progress')
    content_completed = models.BooleanField(default=False)
    assessment_passed = models.BooleanField(default=False)
    best_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    best_quiz_taker = models.ForeignKey(
        QuizTaker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='module_progress_records'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'module']
        ordering = ['module__order', 'module__id']

    def __str__(self):
        return f"{self.student.user.username} - {self.module.title}"

    @property
    def completed(self):
        return self.content_completed and self.assessment_passed

    @property
    def unlocks_next(self):
        if getattr(self.module, 'skip_assessment', False):
            return self.content_completed
        return self.assessment_passed

    def refresh_completion(self, save=True):
        completed_now = self.completed
        if completed_now and not self.completed_at:
            self.completed_at = timezone.now()
        elif not completed_now:
            self.completed_at = None

        if save:
            self.save()
        return completed_now


class CertificateTemplate(models.Model):
    TEMPLATE_STYLE_CHOICES = (
        ('classic', _('Classic')),
        ('modern', _('Modern')),
        ('minimal', _('Minimal')),
        ('academic', _('Academic')),
        ('corporate', _('Corporate')),
    )
    ORIENTATION_CHOICES = (
        ('landscape', _('Landscape')),
        ('portrait', _('Portrait')),
    )
    BACKGROUND_STYLE_CHOICES = (
        ('plain', _('Plain')),
        ('gradient', _('Gradient')),
        ('bordered', _('Bordered')),
        ('watermark', _('Watermark')),
    )
    BORDER_STYLE_CHOICES = (
        ('none', _('None')),
        ('thin', _('Thin')),
        ('double', _('Double')),
        ('premium', _('Premium Frame')),
    )
    FONT_STYLE_CHOICES = (
        ('serif', _('Serif')),
        ('sans', _('Sans Serif')),
        ('modern', _('Modern')),
        ('academic', _('Academic')),
    )
    STATUS_CHOICES = (
        ('draft', _('Draft')),
        ('active', _('Active')),
        ('archived', _('Archived')),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="certificate_templates")
    title = models.CharField(max_length=255, default="Certificate of Completion")
    subtitle = models.CharField(max_length=255, blank=True)
    organization_name = models.CharField(max_length=255, default="ChuoSmart Academy")
    instructor_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    template_style = models.CharField(max_length=50, choices=TEMPLATE_STYLE_CHOICES, default="modern")
    orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, default="landscape")
    primary_color = models.CharField(max_length=20, default="#0d6efd")
    secondary_color = models.CharField(max_length=20, default="#111827")
    accent_color = models.CharField(max_length=20, default="#1FAA59")
    background_style = models.CharField(max_length=50, choices=BACKGROUND_STYLE_CHOICES, default="plain")
    border_style = models.CharField(max_length=50, choices=BORDER_STYLE_CHOICES, default="premium")
    font_style = models.CharField(max_length=50, choices=FONT_STYLE_CHOICES, default="serif")
    logo = models.ImageField(upload_to="certificates/logos/", blank=True, null=True)
    signature_image = models.ImageField(upload_to="certificates/signatures/", blank=True, null=True)
    seal_image = models.ImageField(upload_to="certificates/seals/", blank=True, null=True)
    watermark_image = models.ImageField(upload_to="certificates/watermarks/", blank=True, null=True)
    certificate_body = models.TextField(
        blank=True,
        default="This certificate is proudly presented to {{ student_name }} for successfully completing {{ course_title }} on {{ completion_date }}."
    )
    recipient_name_format = models.CharField(max_length=100, default="{{ student_name }}")
    course_name_display = models.CharField(max_length=150, default="{{ course_title }}")
    completion_date_display = models.CharField(max_length=100, default="{{ completion_date }}")
    certificate_id_display = models.CharField(max_length=100, default="{{ certificate_id }}")
    instructor_signature_text = models.CharField(max_length=255, blank=True)
    footer_note = models.TextField(blank=True)
    completion_percentage = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    enable_verification = models.BooleanField(default=True)
    show_qr_code = models.BooleanField(default=True)
    show_certificate_id = models.BooleanField(default=True)
    verification_url_format = models.CharField(max_length=255, blank=True)
    expires = models.BooleanField(default=False)
    validity_months = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['course', '-updated_at']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def clean(self):
        super().clean()
        import re
        color_re = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')
        for field_name in ('primary_color', 'secondary_color', 'accent_color'):
            if not color_re.match(getattr(self, field_name) or ''):
                raise ValidationError({field_name: _('Enter a valid hex color, for example #1E40AF.')})

        if self.expires and not self.validity_months:
            raise ValidationError({'validity_months': _('Set a validity period when certificates expire.')})


class StudentCertificate(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_certificates')
    template = models.ForeignKey(CertificateTemplate, on_delete=models.SET_NULL, null=True)
    certificate_id = models.CharField(max_length=100, unique=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-issued_at']

    def __str__(self):
        return f"{self.certificate_id} - {self.student.username}"

    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = self.generate_certificate_id()

        if self.template and self.template.expires and self.template.validity_months and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=self.template.validity_months * 30)

        super().save(*args, **kwargs)

    @staticmethod
    def generate_certificate_id():
        return f"CHUO-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:10].upper()}"

    @property
    def is_expired(self):
        return bool(self.expires_at and timezone.now() > self.expires_at)

    @property
    def verification_status(self):
        if not self.is_valid:
            return _('Revoked')
        if self.is_expired:
            return _('Expired')
        return _('Valid')


class StudentAnswer(models.Model):
    """
    Student's answer to a question
    """
    quiz_taker = models.ForeignKey(QuizTaker, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    # For MC questions
    mc_answer = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    # For T/F questions  
    tf_answer = models.BooleanField(null=True, blank=True)
    # For essay questions
    essay_text_answer = models.TextField(null=True, blank=True)
    essay_file_answer = models.FileField(upload_to='lms/essay_answers/', null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['quiz_taker', 'question']


class Grade(models.Model):
    """
    Course grade for a student
    """
    student = models.ForeignKey(LMSProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    
    attendance = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    assignment = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    mid_exam = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_exam = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade = models.CharField(max_length=5, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['student', 'course', 'semester']
        
    def __str__(self):
        return f"{self.student.user.username} - {self.course.title} - {self.grade}"
    
    def calculate_total(self):
        self.total = self.attendance + self.assignment + self.mid_exam + self.final_exam
        return self.total
    
    def calculate_grade(self):
        total = self.calculate_total()
        if total >= 90:
            return 'A'
        elif total >= 80:
            return 'B'
        elif total >= 70:
            return 'C'
        elif total >= 60:
            return 'D'
        else:
            return 'F'
    
    def save(self, *args, **kwargs):
        self.total = self.calculate_total()
        self.grade = self.calculate_grade()
        
        if self.grade == 'F':
            self.comment = "Failed. Please retake the course."
        elif self.grade == 'D':
            self.comment = "Passed with warning. Consider reviewing course materials."
        else:
            self.comment = "Passed successfully."
            
        super().save(*args, **kwargs)


class InstructorRequest(models.Model):
    """
    Model to handle requests to become an instructor
    """
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('denied', _('Denied')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructor_requests')
    reason = models.TextField(help_text=_("Explain why you want to become an instructor"))
    qualifications = models.TextField(help_text=_("Describe your qualifications and experience"))
    cv = models.FileField(upload_to='lms/instructor_requests/cv/', blank=True, null=True, 
                         help_text=_("Upload your CV or resume (optional)"))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True, 
                                 help_text=_("Admin notes about this request (not visible to the requester)"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-created_at']


# SiteSettings class moved to site_settings.py


def unique_slug_generator(instance, new_slug=None):
    """
    Generate a unique slug for models
    Handle emojis and ensure the slug isn't too long
    """
    try:
        max_length = instance._meta.get_field('slug').max_length or 50
    except Exception:
        max_length = 50

    if new_slug is not None:
        slug = new_slug[:max_length]
    else:
        # Remove any emojis or special characters that can't be properly slugified
        import re
        import unicodedata
        
        # Normalize and strip non-ASCII characters
        title = unicodedata.normalize('NFKD', instance.title)
        title = ''.join([c for c in title if not unicodedata.combining(c) and c.isascii()])
        
        # If title is empty after filtering, use a generic name plus random string
        if not title.strip():
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            title = f"course-{random_string}"
        
        # Create slug and limit to the model field length to avoid DB field length issues
        slug = slugify(title)[:max_length]
    
    # Get the model class
    Klass = instance.__class__
    
    # Check if slug exists
    qs_exists = Klass.objects.filter(slug=slug).exists()
    if qs_exists:
        # Generate random string
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        suffix = f"-{random_string}"
        new_slug = f"{slug[:max(0, max_length - len(suffix))]}{suffix}"
        return unique_slug_generator(instance, new_slug=new_slug)
    return slug


@receiver(pre_save, sender=Course)
def course_pre_save_receiver(sender, instance, **kwargs):
    """
    Generate slug before saving Course instance
    """
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)


@receiver(pre_save, sender=Quiz)
def quiz_pre_save_receiver(sender, instance, **kwargs):
    """
    Generate slug before saving Quiz instance
    """
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)


@receiver(post_save, sender=Course)
def log_course_save(sender, instance, created, **kwargs):
    """
    Log when a course is created or updated
    """
    verb = "created" if created else "updated"
    ActivityLog.objects.create(message=_(f"The course '{instance}' has been {verb}."))


@receiver(post_delete, sender=Course)
def log_course_delete(sender, instance, **kwargs):
    """
    Log when a course is deleted
    """
    ActivityLog.objects.create(message=_(f"The course '{instance}' has been deleted."))


@receiver(post_save, sender=Program)
def log_program_save(sender, instance, created, **kwargs):
    """
    Log when a program is created or updated
    """
    verb = "created" if created else "updated"
    ActivityLog.objects.create(message=_(f"The program '{instance}' has been {verb}."))


@receiver(post_delete, sender=Program)
def log_program_delete(sender, instance, **kwargs):
    """
    Log when a program is deleted
    """
    ActivityLog.objects.create(message=_(f"The program '{instance}' has been deleted."))


@receiver(pre_save, sender=CourseEnrollment)
def enrollment_payment_status_change(sender, instance, **kwargs):
    """
    Track payment status changes for course enrollments
    """
    if instance.pk:  # Only for existing instances (updates)
        old_instance = CourseEnrollment.objects.get(pk=instance.pk)
        if old_instance.payment_status != instance.payment_status:
            # Payment status changed
            if instance.payment_status == 'approved':
                instance.payment_approved_date = timezone.now()
                ActivityLog.objects.create(
                    message=_(f"Payment for '{instance.course}' by {instance.student.user.username} has been approved.")
                )
            elif instance.payment_status == 'rejected':
                ActivityLog.objects.create(
                    message=_(f"Payment for '{instance.course}' by {instance.student.user.username} has been rejected.")
                )
