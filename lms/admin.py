"""
Admin interface for the LMS app
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from .models import (
    ActivityLog, Semester, LMSProfile, Program, Course, CourseModule, 
    CourseContent, Quiz, Question, MCQuestion, Choice, TF_Question, 
    Essay_Question, QuizTaker, StudentAnswer, Grade, CourseEnrollment,
    InstructorRequest, ContentAccess, SiteSettings, AdExemptUser, PaymentMethod
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
    readonly_fields = ('date_enrolled', 'payment_date', 'payment_approved_date')
    fields = ('student', 'date_enrolled', 'payment_status', 'payment_proof', 'payment_method', 'payment_notes')


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
    list_display = ('title', 'code', 'program', 'level', 'semester', 'year', 'is_free')
    list_filter = ('program', 'level', 'semester', 'year', 'is_elective', 'is_free')
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


# The CourseEnrollmentAdmin class is now defined below with payment management features


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


class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin for site settings"""
    fieldsets = (
        (_('Advertisement Settings'), {
            'fields': ('show_ads_before_free_courses',),
            'description': _('Configure whether advertisements should be shown before users can access free courses.')
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one instance of SiteSettings
        return SiteSettings.objects.count() == 0
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deleting the settings
        return False


@admin.register(AdExemptUser)
class AdExemptUserAdmin(admin.ModelAdmin):
    """Admin interface for AdExemptUser model"""
    list_display = ('user', 'reason', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'reason')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)
    list_filter = ('created_at',)
    
    def get_queryset(self, request):
        """Optimize queries by prefetching related user"""
        return super().get_queryset(request).select_related('user')


# Register all question types
admin.site.register(MCQuestion, MCQuestionAdmin)
admin.site.register(TF_Question, TFQuestionAdmin)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin interface for payment methods"""
    list_display = ('name', 'payment_number', 'instructor', 'is_active')
    list_filter = ('is_active', 'instructor')
    search_fields = ('name', 'payment_number', 'instructor__user__username')


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    """Admin interface for course enrollments with payment management"""
    list_display = ('student', 'course', 'date_enrolled', 'payment_status')
    list_filter = ('payment_status', 'date_enrolled')
    search_fields = ('student__user__username', 'student__user__email', 'course__title')
    readonly_fields = ('date_enrolled', 'payment_date', 'payment_approved_date', 'payment_approved_by')
    raw_id_fields = ('student', 'course')
    fieldsets = (
        (_('Enrollment Information'), {
            'fields': ('student', 'course', 'date_enrolled')
        }),
        (_('Payment Information'), {
            'fields': ('payment_status', 'payment_proof', 'payment_method', 'payment_date', 
                     'payment_approved_by', 'payment_approved_date', 'payment_notes')
        }),
    )
    
    actions = ['approve_payments', 'reject_payments']
    
    def approve_payments(self, request, queryset):
        """Bulk approve pending payments"""
        updated = 0
        for enrollment in queryset.filter(payment_status='pending'):
            enrollment.payment_status = 'approved'
            enrollment.payment_approved_by = request.user
            enrollment.payment_approved_date = timezone.now()
            enrollment.save()
            updated += 1
        
        if updated > 0:
            messages.success(request, _(f"{updated} payment(s) successfully approved."))
        else:
            messages.info(request, _("No pending payments were selected."))
    
    approve_payments.short_description = _("Approve selected payments")
    
    def reject_payments(self, request, queryset):
        """Bulk reject pending payments"""
        updated = 0
        for enrollment in queryset.filter(payment_status='pending'):
            enrollment.payment_status = 'rejected'
            enrollment.payment_notes = _("Payment proof rejected by admin.")
            enrollment.save()
            updated += 1
        
        if updated > 0:
            messages.success(request, _(f"{updated} payment(s) rejected."))
        else:
            messages.info(request, _("No pending payments were selected."))
    
    reject_payments.short_description = _("Reject selected payments")
admin.site.register(Essay_Question, EssayQuestionAdmin)
admin.site.register(SiteSettings, SiteSettingsAdmin)
