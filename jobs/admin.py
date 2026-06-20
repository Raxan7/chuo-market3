import logging
from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.template.response import TemplateResponse
from .models import (
    Company, Industry, Skill, Job, JobApplication, 
    SavedJob, JobSearchPreference, ApiConfiguration, ApiRequestLog, UserJobApproval,
    JobCourseRecommendation,
)
from .api_integration import fetch_jobs_from_api
from .recommendations import get_recommendations

admin_logger = logging.getLogger('jobs.admin')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'is_verified', 'created_by', 'created_at')
    list_filter = ('is_verified', 'country', 'city')
    search_fields = ('name', 'description', 'address', 'city')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Company Details'), {
            'fields': ('name', 'description', 'logo', 'website')
        }),
        (_('Contact Information'), {
            'fields': ('address', 'city', 'country', 'email', 'phone')
        }),
        (_('Status'), {
            'fields': ('is_verified', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(UserJobApproval)
class UserJobApprovalAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_approved', 'approved_by', 'approved_date')
    list_filter = ('is_approved', 'approved_date')
    search_fields = ('user__username', 'user__email', 'approved_by__username')
    readonly_fields = ('approved_date',)
    
    fieldsets = (
        (_('Approval Details'), {
            'fields': ('user', 'is_approved', 'approved_by', 'reason')
        }),
        (_('Timestamps'), {
            'fields': ('approved_date',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if obj.is_approved and not obj.approved_by:
            obj.approved_by = request.user
            obj.approved_date = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'posted_date', 'is_active', 'source')
    list_filter = ('is_active', 'is_featured', 'job_type', 'experience_level', 'is_remote', 'source', 'posted_date')
    search_fields = ('title', 'description', 'requirements', 'company__name', 'location', 'external_id')
    readonly_fields = ('views_count', 'applications_count', 'posted_date', 'created_by')
    filter_horizontal = ('skills',)
    date_hierarchy = 'posted_date'
    fieldsets = (
        (_('Job Details'), {
            'fields': ('title', 'description', 'company', 'industry', 'location', 'is_remote')
        }),
        (_('Salary Information'), {
            'fields': ('salary_min', 'salary_max', 'salary_currency')
        }),
        (_('Job Requirements'), {
            'fields': ('job_type', 'experience_level', 'requirements', 'responsibilities', 'benefits', 'skills')
        }),
        (_('Dates'), {
            'fields': ('application_deadline', 'posted_date')
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_featured', 'views_count', 'applications_count', 'created_by')
        }),
        (_('API Information'), {
            'fields': ('source', 'external_id', 'external_url'),
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company', 'created_by')

    actions = ['view_course_recommendations']

    def view_course_recommendations(self, request, queryset):
        selected = queryset[:1]
        if not selected:
            self.message_user(request, 'No jobs selected.', level='WARNING')
            return
        job = selected[0]
        return HttpResponseRedirect(
            reverse('admin:jobs_job_recommendations', args=[job.id])
        )
    view_course_recommendations.short_description = _('View course recommendations for selected job')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:job_id>/recommendations/',
                self.admin_site.admin_view(self.recommendations_view),
                name='jobs_job_recommendations',
            ),
        ]
        return custom_urls + urls

    def recommendations_view(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)

        if request.method == 'POST' and '_regenerate' in request.POST:
            JobCourseRecommendation.objects.filter(job=job).delete()
            messages.success(request, 'Recommendations cache cleared. Regenerating...')

        rec_data = {'items': [], 'cached': False}
        try:
            items = get_recommendations(job)
            cached = JobCourseRecommendation.objects.filter(job=job).exists()
            rec_data = {'items': items, 'cached': cached}
        except Exception as e:
            admin_logger.error('Recommendation admin error: %s', e, exc_info=True)
            messages.error(request, f'Error generating recommendations: {e}')

        context = {
            'title': f'Course Recommendations - {job.title}',
            'job': job,
            'recommendations': rec_data['items'],
            'cached': rec_data['cached'],
            'opts': self.model._meta,
            'has_view_permission': True,
            'add': False,
            'change': False,
            'is_popup': False,
            'save_as': False,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request),
            'has_delete_permission': self.has_delete_permission(request),
            'has_editable_inline_admin_formsets': False,
        }
        return TemplateResponse(
            request, 'admin/jobs/job_recommendations.html', context
        )
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'applicant', 'status', 'applied_date')
    list_filter = ('status', 'applied_date')
    search_fields = ('job__title', 'applicant__username', 'applicant__email', 'cover_letter')
    readonly_fields = ('applied_date', 'updated_date')
    fieldsets = (
        (_('Application'), {
            'fields': ('job', 'applicant', 'cover_letter', 'resume', 'status')
        }),
        (_('Employer Feedback'), {
            'fields': ('employer_notes',)
        }),
        (_('Dates'), {
            'fields': ('applied_date', 'updated_date')
        }),
    )


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'saved_date')
    list_filter = ('saved_date',)
    search_fields = ('job__title', 'user__username', 'user__email')
    readonly_fields = ('saved_date',)


@admin.register(JobSearchPreference)
class JobSearchPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_notifications', 'notification_frequency', 'updated_at')
    list_filter = ('email_notifications', 'notification_frequency')
    search_fields = ('user__username', 'user__email', 'keywords', 'locations')
    filter_horizontal = ('industries', 'skills')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Job Preferences'), {
            'fields': ('job_types', 'locations', 'keywords', 'industries', 'skills', 'experience_levels', 'salary_min')
        }),
        (_('Notification Settings'), {
            'fields': ('email_notifications', 'notification_frequency')
        }),
        (_('Dates'), {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ApiConfiguration)
class ApiConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'last_fetch_date', 'request_count')
    list_filter = ('is_active', 'name')
    readonly_fields = ('last_fetch_date', 'request_count', 'created_at', 'updated_at')
    fieldsets = (
        (_('API Details'), {
            'fields': ('name', 'api_key', 'api_secret', 'additional_params')
        }),
        (_('Status'), {
            'fields': ('is_active', 'daily_limit', 'request_count', 'last_fetch_date')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['run_api_fetch']
    
    def run_api_fetch(self, request, queryset):
        """Admin action to manually fetch jobs from selected API configurations"""
        total_created = 0
        total_updated = 0
        for config in queryset:
            if not config.is_active:
                self.message_user(
                    request, 
                    f"Skipped {config.name} - API configuration is not active", 
                    level=messages.WARNING
                )
                continue
                
            try:
                saved_jobs, created, updated = fetch_jobs_from_api(config.name)
                total_created += created
                total_updated += updated
                self.message_user(
                    request, 
                    f"Successfully fetched jobs from {config.name}. Created: {created}, Updated: {updated}",
                    level=messages.SUCCESS
                )
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error fetching jobs from {config.name}: {str(e)}", 
                    level=messages.ERROR
                )
        
        self.message_user(
            request, 
            f"Job fetch completed. Total created: {total_created}, Total updated: {total_updated}",
            level=messages.INFO
        )
    
    run_api_fetch.short_description = _("Fetch jobs from selected APIs")


@admin.register(ApiRequestLog)
class ApiRequestLogAdmin(admin.ModelAdmin):
    list_display = ('api_config', 'endpoint', 'response_status', 'jobs_fetched', 'jobs_created', 'request_date')
    list_filter = ('api_config', 'response_status', 'request_date')
    readonly_fields = ('api_config', 'endpoint', 'request_params', 'response_status', 'response_data', 
                      'error_message', 'request_date', 'execution_time', 'jobs_fetched', 'jobs_created', 'jobs_updated')
    fieldsets = (
        (_('Request Details'), {
            'fields': ('api_config', 'endpoint', 'request_params', 'request_date')
        }),
        (_('Response'), {
            'fields': ('response_status', 'response_data', 'error_message', 'execution_time')
        }),
        (_('Results'), {
            'fields': ('jobs_fetched', 'jobs_created', 'jobs_updated')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(JobCourseRecommendation)
class JobCourseRecommendationAdmin(admin.ModelAdmin):
    list_display = ('job', 'source', 'course_count', 'updated_at')
    list_filter = ('source', 'updated_at')
    search_fields = ('job__title',)
    readonly_fields = ('created_at', 'updated_at')

    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = _('Courses')

    def has_add_permission(self, request):
        return False
