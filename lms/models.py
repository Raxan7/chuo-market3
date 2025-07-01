"""
Models for the LMS application, based on SkyLearn but adapted for chuo-market3
"""

from django.db import models
from django.urls import reverse
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import random
import string
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
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


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
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    code = models.CharField(max_length=20, unique=True)
    credit = models.IntegerField(default=3)
    summary = models.TextField(blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    level = models.CharField(max_length=2, choices=LEVEL_CHOICES)
    year = models.IntegerField(choices=YEARS, default=1)
    semester = models.CharField(choices=SEMESTER_CHOICES, max_length=10)
    is_elective = models.BooleanField(default=False)
    image = models.ImageField(upload_to='lms/course_images/', blank=True, null=True)
    instructors = models.ManyToManyField(LMSProfile, related_name='courses_teaching',
                                        limit_choices_to={'role': 'instructor'})
    students = models.ManyToManyField(LMSProfile, through='CourseEnrollment', 
                                     related_name='courses_enrolled')
    
    def __str__(self):
        return f"{self.title} ({self.code})"
    
    def get_absolute_url(self):
        return reverse("lms:course_detail", kwargs={"slug": self.slug})
    
    @property
    def is_current_semester(self):
        current_semester = Semester.objects.filter(is_current_semester=True).first()
        return self.semester == current_semester.semester if current_semester else False


class CourseEnrollment(models.Model):
    """
    Represents a student's enrollment in a course
    """
    student = models.ForeignKey(LMSProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'course']
    
    def __str__(self):
        return f"{self.student.user.username} enrolled in {self.course.title}"


class CourseModule(models.Model):
    """
    A module within a course (chapter or section)
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.title} - {self.course.title}"


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


class Quiz(models.Model):
    """
    Quiz model for assessments
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(verbose_name=_("Title"), max_length=60)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        help_text=_("A detailed description of the quiz")
    )
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
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
        default=50,
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
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")
        ordering = ['course', 'title']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse("lms:quiz_detail", kwargs={"slug": self.slug})


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


def unique_slug_generator(instance, new_slug=None):
    """
    Generate a unique slug for models
    """
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.title)
    
    # Get the model class
    Klass = instance.__class__
    
    # Check if slug exists
    qs_exists = Klass.objects.filter(slug=slug).exists()
    if qs_exists:
        # Generate random string
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        new_slug = f"{slug}-{random_string}"
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
