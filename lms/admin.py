"""
Admin interface for the LMS app
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    ActivityLog, Semester, LMSProfile, Program, Course, CourseModule, 
    CourseContent, Quiz, Question, MCQuestion, Choice, TF_Question, 
    Essay_Question, QuizTaker, StudentAnswer, Grade, CourseEnrollment,
    InstructorRequest, ContentAccess
)


class CourseModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 1


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class CourseEnrollmentInline(admin.TabularInline):
    model = CourseEnrollment
    extra = 1
    readonly_fields = ('date_enrolled',)


@admin.register(LMSProfile)
class LMSProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title', 'summary')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'program', 'level', 'semester', 'year')
    list_filter = ('program', 'level', 'semester', 'year', 'is_elective')
    search_fields = ('title', 'code', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [CourseModuleInline, CourseEnrollmentInline]
    filter_horizontal = ('instructors',)


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'description', 'course__title')
    ordering = ('course', 'order')


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'content_type', 'order')
    list_filter = ('content_type', 'module__course')
    search_fields = ('title', 'text_content', 'module__title')
    ordering = ('module', 'order')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'category', 'draft', 'due_date')
    list_filter = ('course', 'category', 'draft')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ()
    fieldsets = (
        (None, {
            'fields': ('course', 'module', 'title', 'slug', 'description', 'category')
        }),
        (_('Options'), {
            'fields': ('random_order', 'answers_at_end', 'exam_paper', 'single_attempt', 'pass_mark', 'draft', 'due_date')
        })
    )


class MCQuestionAdmin(admin.ModelAdmin):
    list_display = ('content', 'quiz', 'order')
    list_filter = ('quiz',)
    search_fields = ('content', 'explanation')
    fields = ('quiz', 'figure', 'content', 'explanation', 'order', 'choice_order')
    inlines = [ChoiceInline]


class TFQuestionAdmin(admin.ModelAdmin):
    list_display = ('content', 'quiz', 'order')
    list_filter = ('quiz',)
    search_fields = ('content', 'explanation')
    fields = ('quiz', 'figure', 'content', 'explanation', 'correct', 'order')


class EssayQuestionAdmin(admin.ModelAdmin):
    list_display = ('content', 'quiz', 'order')
    list_filter = ('quiz',)
    search_fields = ('content', 'explanation')
    fields = ('quiz', 'figure', 'content', 'explanation', 'answer_type', 'order')


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'semester', 'attendance', 'assignment', 'mid_exam', 'final_exam', 'total', 'grade')
    list_filter = ('course', 'semester', 'grade')
    search_fields = ('student__user__username', 'student__user__first_name', 'student__user__last_name', 'course__title')
    readonly_fields = ('total', 'grade', 'comment')


@admin.register(QuizTaker)
class QuizTakerAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'completed', 'date_started', 'date_completed')
    list_filter = ('completed', 'quiz')
    search_fields = ('user__user__username', 'quiz__title')
    readonly_fields = ('date_started',)


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('quiz_taker', 'question', 'is_correct')
    list_filter = ('is_correct',)
    readonly_fields = ('quiz_taker', 'question', 'mc_answer', 'tf_answer', 'essay_text_answer', 'essay_file_answer', 'is_correct')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'message')
    search_fields = ('message',)
    readonly_fields = ('timestamp', 'message')
    

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('year', 'semester', 'is_current_semester')
    list_filter = ('year', 'semester', 'is_current_semester')


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'date_enrolled')
    list_filter = ('course',)
    search_fields = ('student__user__username', 'student__user__first_name', 'student__user__last_name', 'course__title')
    readonly_fields = ('date_enrolled',)


@admin.register(InstructorRequest)
class InstructorRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('user', 'reason', 'qualifications', 'cv', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'reason', 'qualifications', 'cv')
        }),
        (_('Request Status'), {
            'fields': ('status', 'admin_notes')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'deny_requests']
    
    def approve_requests(self, request, queryset):
        for instructor_request in queryset.filter(status='pending'):
            # Update request status
            instructor_request.status = 'approved'
            instructor_request.save()
            
            # Update user profile role to instructor
            profile = instructor_request.user.lms_profile
            profile.role = 'instructor'
            profile.save()
            
            # Log the activity
            ActivityLog.objects.create(
                message=_(f"User {instructor_request.user.username}'s instructor request was approved.")
            )
        
        self.message_user(request, _("Selected requests have been approved."))
    approve_requests.short_description = _("Approve selected instructor requests")
    
    def deny_requests(self, request, queryset):
        for instructor_request in queryset.filter(status='pending'):
            # Update request status
            instructor_request.status = 'denied'
            instructor_request.save()
            
            # Log the activity
            ActivityLog.objects.create(
                message=_(f"User {instructor_request.user.username}'s instructor request was denied.")
            )
        
        self.message_user(request, _("Selected requests have been denied."))
    deny_requests.short_description = _("Deny selected instructor requests")


@admin.register(ContentAccess)
class ContentAccessAdmin(admin.ModelAdmin):
    list_display = ('student', 'content', 'accessed_at', 'completed', 'completed_at')
    list_filter = ('completed', 'accessed_at', 'completed_at')
    search_fields = ('student__user__username', 'content__title')
    readonly_fields = ('accessed_at',)


# Register all question types
admin.site.register(MCQuestion, MCQuestionAdmin)
admin.site.register(TF_Question, TFQuestionAdmin)
admin.site.register(Essay_Question, EssayQuestionAdmin)
