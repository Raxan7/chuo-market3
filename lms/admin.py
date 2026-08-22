"""
Admin interface for the LMS app
"""

from decimal import Decimal, InvalidOperation

from django.contrib import admin
from django.contrib.admin import helpers
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from .models import (
    ActivityLog, Semester, LMSProfile, Program, Course, CourseModule, 
    CourseContent, Quiz, Question, MCQuestion, Choice, TF_Question, 
    Essay_Question, QuizTaker, StudentAnswer, Grade, CourseEnrollment,
    InstructorRequest, ContentAccess, ModuleAccessGrant, SiteSettings, AdExemptUser, PaymentMethod,
    ModuleProgress, CertificateTemplate, StudentCertificate, CoursePayment, CertificatePayment,
    ModulePayment, ModuleAccessRequest,
)


class CourseModuleInline(admin.TabularInline):
    model = CourseModule
    extra = 1


class ModuleAccessGrantInline(admin.TabularInline):
    model = ModuleAccessGrant
    extra = 1
    raw_id_fields = ('student',)
    readonly_fields = ('granted_at',)
    fields = ('student', 'active', 'notes', 'granted_at')


class ModuleAccessRequestInline(admin.TabularInline):
    model = ModuleAccessRequest
    extra = 0
    can_delete = False
    raw_id_fields = ('student',)
    readonly_fields = ('status', 'requested_at', 'approved_at')
    fields = ('student', 'status', 'payment', 'notes', 'requested_at', 'approved_at')


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class CourseEnrollmentInline(admin.TabularInline):
    model = CourseEnrollment
    extra = 1
    readonly_fields = ('date_enrolled', 'payment_date', 'payment_approved_date')
    fields = ('student', 'date_enrolled', 'payment_status', 'payment_proof', 'payment_method', 'payment_notes', 'admin_granted_access', 'admin_granted_certificate', 'certificate_prepaid')


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
    list_display = ('title', 'code', 'program', 'level', 'semester', 'year', 'is_free', 'is_pinned')
    list_filter = ('program', 'level', 'semester', 'year', 'is_elective', 'is_free', 'is_pinned')
    list_editable = ('is_pinned',)
    search_fields = ('title', 'code', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [CourseModuleInline, CourseEnrollmentInline]
    filter_horizontal = ('instructors',)


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'price', 'skip_assessment')
    list_filter = ('course',)
    list_editable = ('price',)
    search_fields = ('title', 'description', 'course__title')
    ordering = ('course', 'order')
    inlines = [ModuleAccessGrantInline, ModuleAccessRequestInline]
    actions = ('bulk_set_price',)
    fieldsets = (
        (None, {
            'fields': ('title', 'course', 'order', 'price', 'skip_assessment', 'description')
        }),
        (_('Module Access Pricing'), {
            'description': _(
                'Set a price to enable students to pay online and request access to '
                'this single module. Leave blank to hide the "Request Access" option.'
            ),
            'fields': (),
        }),
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, ModuleAccessGrant) and not instance.granted_by_id:
                instance.granted_by = request.user
            instance.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    @admin.action(description=_('Set price for selected modules (bulk)'))
    def bulk_set_price(self, request, queryset):
        """Show the confirmation page to apply a single price to many modules.

        Since most modules within a course share the same price, this saves
        editing each module individually in the admin.
        """
        return self._render_bulk_price_form(request, queryset)

    def _render_bulk_price_form(self, request, queryset):
        context = {
            **self.admin_site.each_context(request),
            'title': _('Set price for modules'),
            'opts': self.model._meta,
            'media': self.media,
            'queryset': queryset,
            'queryset_count': queryset.count(),
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }
        return render(request, 'admin/lms/coursemodule/bulk_set_price.html', context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-set-price/',
                self.admin_site.admin_view(self.bulk_set_price_view),
                name='lms_coursemodule_bulk_set_price',
            ),
        ]
        return custom_urls + urls

    def bulk_set_price_view(self, request):
        """Handle the price submission from the bulk-set-price confirmation page."""
        if request.method != 'POST':
            return HttpResponseRedirect(reverse('admin:lms_coursemodule_changelist'))

        ids = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        queryset = self.get_queryset(request).filter(pk__in=ids)
        if not queryset.exists():
            self.message_user(request, _('No modules were selected.'), level=messages.WARNING)
            return HttpResponseRedirect(reverse('admin:lms_coursemodule_changelist'))

        price = request.POST.get('price', '').strip()
        apply_to_course = request.POST.get('apply_to_course') == 'on'

        new_price = None
        if price:
            try:
                new_price = Decimal(price)
            except InvalidOperation:
                self.message_user(
                    request,
                    _('Invalid price "%(price)s". Enter a valid number or leave blank to clear the price.') % {
                        'price': price,
                    },
                    level=messages.ERROR,
                )
                return self._render_bulk_price_form(request, queryset)

        if apply_to_course:
            course_ids = list(queryset.values_list('course_id', flat=True).distinct())
            updated = CourseModule.objects.filter(course_id__in=course_ids).update(price=new_price)
            self.message_user(
                request,
                _('Set price to %(price)s for %(count)d module(s) across %(courses)d course(s).') % {
                    'price': new_price if new_price is not None else _('empty (free)'),
                    'count': updated,
                    'courses': len(course_ids),
                },
            )
        else:
            updated = queryset.update(price=new_price)
            self.message_user(
                request,
                _('Set price to %(price)s for %(count)d module(s).') % {
                    'price': new_price if new_price is not None else _('empty (free)'),
                    'count': updated,
                },
            )

        return HttpResponseRedirect(reverse('admin:lms_coursemodule_changelist'))


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'content_type', 'order')
    list_filter = ('content_type', 'module__course')
    search_fields = ('title', 'text_content', 'module__title')
    ordering = ('module', 'order')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'generated_for', 'generation_status', 'category', 'draft', 'due_date')
    list_filter = ('course', 'category', 'draft', 'generation_status')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ()
    fieldsets = (
        (None, {
            'fields': ('course', 'module', 'generated_for', 'title', 'slug', 'description', 'category')
        }),
        (_('Options'), {
            'fields': ('random_order', 'answers_at_end', 'exam_paper', 'single_attempt', 'pass_mark', 'draft', 'due_date', 'generation_status', 'generation_message', 'generation_started_at', 'generation_completed_at')
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


@admin.register(ModuleAccessGrant)
class ModuleAccessGrantAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'active', 'granted_by', 'granted_at')
    list_filter = ('active', 'module__course', 'granted_at')
    search_fields = ('student__user__username', 'module__title', 'module__course__title', 'notes')
    readonly_fields = ('granted_at', 'granted_by')
    raw_id_fields = ('student', 'module')

    def save_model(self, request, obj, form, change):
        if not obj.granted_by_id:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ModuleAccessRequest)
class ModuleAccessRequestAdmin(admin.ModelAdmin):
    """Admin interface to review student module access requests.

    Requests are auto-approved once the Snippe payment is completed, which
    creates a ModuleAccessGrant (the existing, working mechanism) and
    auto-enrolls the student in the course. The approve/reject actions remain
    available as a manual override for legacy pending requests.
    """
    list_display = ('student', 'module', 'module_price', 'payment_amount', 'status', 'requested_at', 'approved_at')
    list_filter = ('status', 'requested_at', 'module__course')
    search_fields = ('student__user__username', 'student__user__email', 'module__title', 'module__course__title', 'notes')
    readonly_fields = ('requested_at', 'updated_at', 'approved_at', 'approved_by')
    raw_id_fields = ('student', 'module', 'payment')
    actions = ('approve_requests', 'reject_requests')
    list_select_related = ('student', 'module', 'module__course')

    def module_price(self, obj):
        return obj.module.price
    module_price.short_description = _('Module Price (TZS)')

    def payment_amount(self, obj):
        return obj.payment.amount if obj.payment else '—'
    payment_amount.short_description = _('Paid Amount (TZS)')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    @admin.action(description=_('Approve selected access requests'))
    def approve_requests(self, request, queryset):
        for obj in queryset.filter(status='pending'):
            obj.approve(request.user)
            self.message_user(
                request,
                _('Approved module access for %(student)s on "%(module)s".') % {
                    'student': obj.student.user.username,
                    'module': obj.module.title,
                },
            )

    @admin.action(description=_('Reject selected access requests'))
    def reject_requests(self, request, queryset):
        count = queryset.filter(status='pending').update(status='rejected', approved_by=request.user, approved_at=timezone.now())
        self.message_user(request, _('Rejected %(count)d access request(s).') % {'count': count})


@admin.register(ModulePayment)
class ModulePaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'module', 'amount', 'status', 'created_at', 'snippe_reference')
    list_filter = ('status', 'module__course', 'created_at')
    search_fields = ('user__username', 'module__title', 'snippe_reference', 'snippe_session_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'content_completed', 'assessment_passed', 'best_score', 'completed_at')
    list_filter = ('content_completed', 'assessment_passed', 'module__course')
    search_fields = ('student__user__username', 'module__title', 'module__course__title')
    readonly_fields = ('completed_at', 'updated_at')


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'organization_name', 'completion_percentage', 'status', 'updated_at')
    list_filter = ('status', 'template_style', 'orientation')
    search_fields = ('title', 'course__title', 'organization_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StudentCertificate)
class StudentCertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_id', 'student', 'course', 'issued_at', 'verification_status', 'is_valid')
    list_filter = ('is_valid', 'course', 'issued_at')
    search_fields = ('certificate_id', 'student__username', 'student__email', 'course__title')
    readonly_fields = ('certificate_id', 'issued_at')


class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin for site settings"""
    fieldsets = ()

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
    list_display = ('student', 'course', 'date_enrolled', 'payment_status', 'admin_granted_access', 'admin_granted_certificate', 'certificate_prepaid')
    list_filter = ('payment_status', 'admin_granted_access', 'admin_granted_certificate', 'certificate_prepaid', 'date_enrolled')
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
        (_('Admin Granted Access'), {
            'fields': ('admin_granted_access', 'admin_granted_certificate', 'certificate_prepaid', 'granted_by'),
            'description': _('Grant course access without requiring payment. Certificate access is separate. Use "Certificate prepaid" when the certificate was included in a bundled course payment.')
        }),
    )
    
    actions = ['approve_payments', 'reject_payments', 'grant_course_access', 'grant_certificate_access', 'revoke_admin_granted_access']
    
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
    
    def grant_course_access(self, request, queryset):
        """Grant course access to selected enrollments without requiring payment"""
        updated = 0
        for enrollment in queryset:
            enrollment.admin_granted_access = True
            enrollment.granted_by = request.user
            enrollment.save()
            updated += 1
        
        if updated > 0:
            messages.success(request, _(f"{updated} enrollment(s) granted course access."))
        else:
            messages.info(request, _("No enrollments were updated."))
    
    grant_course_access.short_description = _("Grant course access (no certificate)")
    
    def grant_certificate_access(self, request, queryset):
        """Grant certificate access to selected enrollments in addition to course access"""
        updated = 0
        for enrollment in queryset:
            enrollment.admin_granted_access = True
            enrollment.admin_granted_certificate = True
            enrollment.certificate_prepaid = True
            enrollment.granted_by = request.user
            enrollment.save()
            updated += 1
        
        if updated > 0:
            messages.success(request, _(f"{updated} enrollment(s) granted full access including certificate."))
        else:
            messages.info(request, _("No enrollments were updated."))
    
    grant_certificate_access.short_description = _("Grant full access (course + certificate)")
    
    def revoke_admin_granted_access(self, request, queryset):
        """Revoke admin granted access from selected enrollments"""
        updated = 0
        for enrollment in queryset:
            enrollment.admin_granted_access = False
            enrollment.admin_granted_certificate = False
            enrollment.certificate_prepaid = False
            enrollment.granted_by = None
            enrollment.save()
            updated += 1
        
        if updated > 0:
            messages.success(request, _(f"{updated} enrollment(s) had admin access revoked."))
        else:
            messages.info(request, _("No enrollments were updated."))
    
    revoke_admin_granted_access.short_description = _("Revoke admin granted access")
admin.site.register(Essay_Question, EssayQuestionAdmin)
admin.site.register(SiteSettings, SiteSettingsAdmin)


@admin.register(CoursePayment)
class CoursePaymentAdmin(admin.ModelAdmin):
    """Admin interface for course payments"""
    list_display = ('user', 'course', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'course__title', 'course__id', 'snippe_session_id')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_completed']
    
    def mark_completed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='completed')
        self.message_user(request, _(f"{updated} payment(s) marked as completed."))
    mark_completed.short_description = _("Mark selected as completed")


@admin.register(CertificatePayment)
class CertificatePaymentAdmin(admin.ModelAdmin):
    """Admin interface for certificate payments"""
    list_display = ('user', 'certificate', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'certificate__certificate_id', 'snippe_session_id')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_completed']
    
    def mark_completed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='completed')
        self.message_user(request, _(f"{updated} payment(s) marked as completed."))
    mark_completed.short_description = _("Mark selected as completed")
