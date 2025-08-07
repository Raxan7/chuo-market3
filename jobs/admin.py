from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Company, Industry, Skill, Job, JobApplication, 
    SavedJob, JobSearchPreference, ApiConfiguration, ApiRequestLog
)

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


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'salary_range', 'posted_date', 'is_active')
    list_filter = ('is_active', 'is_featured', 'job_type', 'experience_level', 'is_remote', 'source')
    search_fields = ('title', 'description', 'requirements', 'company__name', 'location')
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
            'classes': ('collapse',)
        }),
    )
    
    def salary_range(self, obj):
        if obj.salary_min and obj.salary_max:
            return f"{obj.salary_min:,} - {obj.salary_max:,} {obj.salary_currency}"
        elif obj.salary_min:
            return f"From {obj.salary_min:,} {obj.salary_currency}"
        elif obj.salary_max:
            return f"Up to {obj.salary_max:,} {obj.salary_currency}"
        return _("Not specified")
    
    salary_range.short_description = _("Salary Range")


@admin.register(JobApplication)
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
    list_display = ('name', 'is_active', 'last_fetch_date', 'request_count', 'daily_limit')
    list_filter = ('is_active', 'name')
    readonly_fields = ('request_count', 'last_fetch_date', 'created_at', 'updated_at')
    fieldsets = (
        (_('API Details'), {
            'fields': ('name', 'is_active')
        }),
        (_('Credentials'), {
            'fields': ('api_key', 'api_secret'),
            'classes': ('collapse',)
        }),
        (_('Additional Settings'), {
            'fields': ('additional_params', 'daily_limit')
        }),
        (_('Status & Statistics'), {
            'fields': ('request_count', 'last_fetch_date', 'created_at', 'updated_at')
        }),
    )


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
