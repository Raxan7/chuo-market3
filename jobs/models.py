from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from tinymce.models import HTMLField
from django.core.validators import MinValueValidator

# Job Types
JOB_TYPE_CHOICES = [
    ('full_time', _('Full Time')),
    ('part_time', _('Part Time')),
    ('contract', _('Contract')),
    ('freelance', _('Freelance')),
    ('internship', _('Internship')),
    ('volunteer', _('Volunteer')),
]

# Experience Levels
EXPERIENCE_LEVEL_CHOICES = [
    ('entry', _('Entry Level')),
    ('mid', _('Mid Level')),
    ('senior', _('Senior Level')),
    ('executive', _('Executive Level')),
]

# Application Status
APPLICATION_STATUS_CHOICES = [
    ('pending', _('Pending')),
    ('reviewed', _('Reviewed')),
    ('shortlisted', _('Shortlisted')),
    ('rejected', _('Rejected')),
    ('interview', _('Interview')),
    ('offered', _('Offered')),
    ('hired', _('Hired')),
]

class Company(models.Model):
    """Model for companies posting jobs"""
    name = models.CharField(_('Company Name'), max_length=100)
    description = HTMLField(_('Description'), blank=True)
    website = models.URLField(_('Website'), blank=True)
    logo = models.ImageField(_('Logo'), upload_to='jobs/company_logos/', blank=True, null=True)
    address = models.CharField(_('Address'), max_length=255, blank=True)
    city = models.CharField(_('City'), max_length=100, blank=True)
    country = models.CharField(_('Country'), max_length=100, default='Tanzania')
    email = models.EmailField(_('Contact Email'), blank=True)
    phone = models.CharField(_('Contact Phone'), max_length=30, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(_('Verified'), default=False)
    
    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('jobs:company_detail', args=[str(self.id)])


class Industry(models.Model):
    """Model for job industries"""
    name = models.CharField(_('Industry Name'), max_length=100)
    
    class Meta:
        verbose_name = _('Industry')
        verbose_name_plural = _('Industries')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Skill(models.Model):
    """Model for job skills"""
    name = models.CharField(_('Skill Name'), max_length=100)
    
    class Meta:
        verbose_name = _('Skill')
        verbose_name_plural = _('Skills')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Job(models.Model):
    """Model for job postings"""
    title = models.CharField(_('Job Title'), max_length=100)
    description = HTMLField(_('Job Description'))
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    industry = models.ForeignKey(Industry, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    location = models.CharField(_('Location'), max_length=100)
    is_remote = models.BooleanField(_('Remote Job'), default=False)
    salary_min = models.DecimalField(_('Minimum Salary'), max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    salary_max = models.DecimalField(_('Maximum Salary'), max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    salary_currency = models.CharField(_('Currency'), max_length=10, default='TZS')
    job_type = models.CharField(_('Job Type'), max_length=20, choices=JOB_TYPE_CHOICES)
    experience_level = models.CharField(_('Experience Level'), max_length=20, choices=EXPERIENCE_LEVEL_CHOICES)
    requirements = HTMLField(_('Requirements'))
    responsibilities = HTMLField(_('Responsibilities'), blank=True)
    benefits = HTMLField(_('Benefits'), blank=True)
    application_deadline = models.DateTimeField(_('Application Deadline'))
    posted_date = models.DateTimeField(_('Posted Date'), default=timezone.now)
    is_active = models.BooleanField(_('Active'), default=True)
    is_featured = models.BooleanField(_('Featured'), default=False)
    views_count = models.PositiveIntegerField(_('Views'), default=0)
    applications_count = models.PositiveIntegerField(_('Applications'), default=0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    skills = models.ManyToManyField(Skill, blank=True, related_name='jobs')
    
    # Job posting type
    job_posting_type = models.CharField(
        _('Job Posting Type'),
        max_length=20,
        choices=[('internal', _('Apply on Chuosmart')), ('external', _('External Link'))],
        default='internal',
        help_text=_('Whether users apply via Chuosmart or are directed to an external site')
    )
    
    # API source fields
    source = models.CharField(_('Source'), max_length=50, blank=True, help_text=_('API source of the job (e.g., LinkedIn, Indeed)'))
    external_id = models.CharField(_('External ID'), max_length=255, blank=True, help_text=_('ID from the external source'))
    external_url = models.URLField(_('External URL'), blank=True, help_text=_('Original job posting URL'))
    
    class Meta:
        verbose_name = _('Job')
        verbose_name_plural = _('Jobs')
        ordering = ['-posted_date']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['location']),
            models.Index(fields=['job_type']),
            models.Index(fields=['source']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        if self.company:
            return f"{self.title} at {self.company.name}"
        return f"{self.title}"
    
    def get_absolute_url(self):
        return reverse('jobs:job_detail', args=[str(self.id)])
    
    def save(self, *args, **kwargs):
        # Ensure salary_max is greater than or equal to salary_min
        if self.salary_min and self.salary_max and self.salary_min > self.salary_max:
            self.salary_max = self.salary_min
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.application_deadline

    @classmethod
    def public_queryset(cls):
        """Return jobs that can be displayed to end users.
        
        Requirements:
        - Must be active
        - Creator must be approved to post visible jobs
        - If there's a company: internal postings require company verification, external always public
        - If no company: always public (user approval is sufficient)
        """
        internal_sources = Q(source__isnull=True) | Q(source="") | Q(source="internal")
        approved_users = User.objects.filter(job_approval__is_approved=True)
        
        # Public if:
        # 1. External source (not internal), OR
        # 2. Internal source with verified company, OR
        # 3. No company (user approval is sufficient)
        return cls.objects.filter(
            is_active=True, 
            created_by__in=approved_users
        ).filter(
            ~internal_sources | 
            (internal_sources & Q(company__is_verified=True)) |
            Q(company__isnull=True)
        )

    @property
    def is_internal_source(self):
        return not self.source or self.source == "internal"

    @property
    def is_public(self):
        if not self.is_active:
            return False
        # Check if user is approved
        try:
            if not self.created_by.job_approval.is_approved:
                return False
        except UserJobApproval.DoesNotExist:
            return False
        # If no company, visibility depends only on user approval
        if not self.company:
            return True
        # If company exists, check if it's verified for internal jobs
        if self.is_internal_source:
            return self.company.is_verified
        return True

    @property
    def visibility_label(self):
        if not self.is_active:
            return _("Inactive")
        try:
            if not self.created_by.job_approval.is_approved:
                return _("Pending user approval")
        except UserJobApproval.DoesNotExist:
            return _("Pending user approval")
        if not self.is_internal_source:
            return _("Public (external source)")
        if not self.company:
            return _("Public")
        if self.company.is_verified:
            return _("Public")
        return _("Hidden until company verification")


class JobApplication(models.Model):
    """Model for job applications"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    cover_letter = models.TextField(_('Cover Letter'))
    resume = models.FileField(_('Resume'), upload_to='jobs/resumes/')
    phone_number = models.CharField(_('Phone Number'), max_length=20, blank=True)
    portfolio_url = models.URLField(_('Portfolio URL'), blank=True)
    additional_documents = models.FileField(_('Additional Documents'), upload_to='jobs/documents/', blank=True, null=True)
    availability = models.CharField(_('Availability'), max_length=100, blank=True)
    salary_expectation = models.DecimalField(_('Salary Expectation (TZS)'), max_digits=12, decimal_places=2, blank=True, null=True)
    status = models.CharField(_('Status'), max_length=20, choices=APPLICATION_STATUS_CHOICES, default='pending')
    applied_date = models.DateTimeField(_('Applied Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    employer_notes = models.TextField(_('Employer Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Job Application')
        verbose_name_plural = _('Job Applications')
        ordering = ['-applied_date']
        # Ensure one application per user per job
        constraints = [
            models.UniqueConstraint(fields=['job', 'applicant'], name='unique_job_application')
        ]
    
    def __str__(self):
        return f"Application for {self.job.title} by {self.applicant.username}"
    
    def get_status_color(self):
        """Return Bootstrap color class for status badges"""
        status_colors = {
            'pending': 'secondary',
            'reviewing': 'warning',
            'shortlisted': 'info',
            'interview': 'primary',
            'offered': 'success',
            'hired': 'success',
            'rejected': 'danger'
        }
        return status_colors.get(self.status, 'secondary')


class SavedJob(models.Model):
    """Model for bookmarked/saved jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saves')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    saved_date = models.DateTimeField(_('Saved Date'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Saved Job')
        verbose_name_plural = _('Saved Jobs')
        ordering = ['-saved_date']
        # Ensure one save per user per job
        constraints = [
            models.UniqueConstraint(fields=['job', 'user'], name='unique_saved_job')
        ]
    
    def __str__(self):
        return f"{self.job.title} saved by {self.user.username}"


class JobSearchPreference(models.Model):
    """Model for user job search preferences for notifications"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='job_preferences')
    job_types = models.CharField(_('Job Types'), max_length=255, blank=True, help_text=_('Comma-separated list of job types'))
    locations = models.CharField(_('Locations'), max_length=255, blank=True, help_text=_('Comma-separated list of locations'))
    keywords = models.CharField(_('Keywords'), max_length=255, blank=True, help_text=_('Comma-separated list of job keywords'))
    industries = models.ManyToManyField(Industry, blank=True, related_name='user_preferences')
    skills = models.ManyToManyField(Skill, blank=True, related_name='user_preferences')
    experience_levels = models.CharField(_('Experience Levels'), max_length=255, blank=True, help_text=_('Comma-separated list of experience levels'))
    salary_min = models.DecimalField(_('Minimum Salary'), max_digits=12, decimal_places=2, null=True, blank=True)
    email_notifications = models.BooleanField(_('Email Notifications'), default=True)
    notification_frequency = models.CharField(_('Notification Frequency'), max_length=20, 
                                             choices=[('daily', _('Daily')), ('weekly', _('Weekly')), ('instant', _('Instant'))],
                                             default='daily')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Job Search Preference')
        verbose_name_plural = _('Job Search Preferences')
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class ApiConfiguration(models.Model):
    """Model for storing API credentials and configuration"""
    name = models.CharField(_('API Name'), max_length=50, unique=True, 
                           choices=[('linkedin', 'LinkedIn'), 
                                   ('indeed', 'Indeed'), 
                                   ('adzuna', 'Adzuna'), 
                                   ('brightermonday', 'BrighterMonday'),
                                   ('ajira', 'Ajira Portal')])
    api_key = models.CharField(_('API Key/Client ID'), max_length=255)
    api_secret = models.CharField(_('API Secret/Client Secret'), max_length=255, blank=True)
    additional_params = models.JSONField(_('Additional Parameters'), default=dict, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    last_fetch_date = models.DateTimeField(_('Last Fetch Date'), null=True, blank=True)
    request_count = models.PositiveIntegerField(_('Request Count'), default=0)
    daily_limit = models.PositiveIntegerField(_('Daily Request Limit'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('API Configuration')
        verbose_name_plural = _('API Configurations')
    
    def __str__(self):
        return f"{self.name} API Configuration"


class ApiRequestLog(models.Model):
    """Model for logging API requests"""
    api_config = models.ForeignKey(ApiConfiguration, on_delete=models.CASCADE, related_name='request_logs')
    endpoint = models.CharField(_('Endpoint'), max_length=255)
    request_params = models.JSONField(_('Request Parameters'), default=dict, blank=True)
    response_status = models.PositiveSmallIntegerField(_('Response Status Code'))
    response_data = models.JSONField(_('Response Data'), null=True, blank=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    request_date = models.DateTimeField(_('Request Date'), auto_now_add=True)
    execution_time = models.FloatField(_('Execution Time (seconds)'), null=True, blank=True)
    jobs_fetched = models.PositiveIntegerField(_('Jobs Fetched'), default=0)
    jobs_created = models.PositiveIntegerField(_('Jobs Created'), default=0)
    jobs_updated = models.PositiveIntegerField(_('Jobs Updated'), default=0)
    
    class Meta:
        verbose_name = _('API Request Log')
        verbose_name_plural = _('API Request Logs')
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.api_config.name} request to {self.endpoint} ({self.response_status})"


class UserJobApproval(models.Model):
    """Track which users are approved to have their job posts visible to the public"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='job_approval')
    is_approved = models.BooleanField(_('Approved to post visible jobs'), default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_users')
    approved_date = models.DateTimeField(_('Approval Date'), null=True, blank=True)
    reason = models.TextField(_('Approval Reason'), blank=True)
    
    class Meta:
        verbose_name = _('User Job Approval')
        verbose_name_plural = _('User Job Approvals')
    
    def __str__(self):
        status = "Approved" if self.is_approved else "Not Approved"
        return f"{self.user.username} - {status}"
