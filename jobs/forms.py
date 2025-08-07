from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from .models import (
    Company, Job, JobApplication, JobSearchPreference,
    Industry, Skill, JOB_TYPE_CHOICES, EXPERIENCE_LEVEL_CHOICES
)


class CompanyForm(forms.ModelForm):
    """Form for creating and updating companies"""
    class Meta:
        model = Company
        fields = ['name', 'description', 'website', 'logo', 'address', 'city', 'country', 'email', 'phone']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'name': forms.TextInput(attrs={'placeholder': _('Company Name')}),
            'website': forms.URLInput(attrs={'placeholder': _('https://example.com')}),
            'address': forms.TextInput(attrs={'placeholder': _('Company Address')}),
            'city': forms.TextInput(attrs={'placeholder': _('City')}),
            'country': forms.TextInput(attrs={'placeholder': _('Country'), 'value': 'Tanzania'}),
            'email': forms.EmailInput(attrs={'placeholder': _('contact@example.com')}),
            'phone': forms.TextInput(attrs={'placeholder': _('+255...')}),
        }


class JobForm(forms.ModelForm):
    """Form for creating and updating jobs"""
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Job
        exclude = ['views_count', 'applications_count', 'created_by', 'source', 'external_id', 'external_url']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('Job Title')}),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': _('Detailed job description...')}),
            'location': forms.TextInput(attrs={'placeholder': _('e.g., Dar es Salaam, Tanzania')}),
            'requirements': forms.Textarea(attrs={'rows': 5, 'placeholder': _('Job requirements...')}),
            'responsibilities': forms.Textarea(attrs={'rows': 5, 'placeholder': _('Job responsibilities...')}),
            'benefits': forms.Textarea(attrs={'rows': 5, 'placeholder': _('Job benefits...')}),
            'application_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'salary_min': forms.NumberInput(attrs={'placeholder': _('Minimum Salary')}),
            'salary_max': forms.NumberInput(attrs={'placeholder': _('Maximum Salary')}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter company choices to those created by the current user
        if self.user and not self.user.is_superuser:
            self.fields['company'].queryset = Company.objects.filter(created_by=self.user)
    
    def clean_application_deadline(self):
        deadline = self.cleaned_data.get('application_deadline')
        if deadline and deadline < timezone.now():
            raise forms.ValidationError(_('Application deadline cannot be in the past.'))
        return deadline
    
    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            self.add_error('salary_max', _('Maximum salary must be greater than or equal to minimum salary.'))
        
        return cleaned_data
    
    def save(self, commit=True):
        job = super().save(commit=False)
        if self.user and not job.created_by_id:
            job.created_by = self.user
        
        if commit:
            job.save()
            self.save_m2m()
        
        return job


class JobApplicationForm(forms.ModelForm):
    """Form for job applications"""
    class Meta:
        model = JobApplication
        fields = ['cover_letter', 'resume']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 5, 'placeholder': _('Your cover letter...')}),
        }
    
    def __init__(self, *args, **kwargs):
        self.job = kwargs.pop('job', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        # Check if user already applied for this job
        if self.job and self.user and JobApplication.objects.filter(job=self.job, applicant=self.user).exists():
            raise forms.ValidationError(_('You have already applied for this job.'))
        return cleaned_data
    
    def save(self, commit=True):
        application = super().save(commit=False)
        if self.job:
            application.job = self.job
        if self.user:
            application.applicant = self.user
        
        if commit:
            application.save()
            # Update job application count
            job = application.job
            job.applications_count = JobApplication.objects.filter(job=job).count()
            job.save(update_fields=['applications_count'])
        
        return application


class JobSearchForm(forms.Form):
    """Form for searching jobs"""
    keywords = forms.CharField(
        label=_('Keywords'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Job title, skills, or company')})
    )
    location = forms.CharField(
        label=_('Location'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('City, region, or country')})
    )
    job_type = forms.MultipleChoiceField(
        label=_('Job Type'),
        required=False,
        choices=JOB_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple
    )
    experience_level = forms.MultipleChoiceField(
        label=_('Experience Level'),
        required=False,
        choices=EXPERIENCE_LEVEL_CHOICES,
        widget=forms.CheckboxSelectMultiple
    )
    industry = forms.ModelChoiceField(
        label=_('Industry'),
        required=False,
        queryset=Industry.objects.all(),
        empty_label=_('All Industries')
    )
    salary_min = forms.DecimalField(
        label=_('Minimum Salary'),
        required=False,
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={'placeholder': _('Min')})
    )
    remote_only = forms.BooleanField(
        label=_('Remote Jobs Only'),
        required=False
    )
    is_featured = forms.BooleanField(
        label=_('Featured Jobs Only'),
        required=False
    )
    posted_since = forms.ChoiceField(
        label=_('Posted Since'),
        required=False,
        choices=[
            ('', _('Any Time')),
            ('1', _('Last 24 Hours')),
            ('7', _('Last 7 Days')),
            ('30', _('Last 30 Days')),
            ('90', _('Last 3 Months')),
        ]
    )


class JobSearchPreferenceForm(forms.ModelForm):
    """Form for job search preferences"""
    class Meta:
        model = JobSearchPreference
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'job_types': forms.TextInput(attrs={'placeholder': _('E.g., full_time, part_time')}),
            'locations': forms.TextInput(attrs={'placeholder': _('E.g., Dar es Salaam, Zanzibar')}),
            'keywords': forms.TextInput(attrs={'placeholder': _('E.g., developer, marketing, finance')}),
            'experience_levels': forms.TextInput(attrs={'placeholder': _('E.g., entry, mid, senior')}),
            'salary_min': forms.NumberInput(attrs={'placeholder': _('Minimum Salary')}),
        }


class ApplicationStatusUpdateForm(forms.ModelForm):
    """Form for updating application status"""
    class Meta:
        model = JobApplication
        fields = ['status', 'employer_notes']
        widgets = {
            'employer_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': _('Notes about this applicant...')})
        }


class CompanyVerificationRequestForm(forms.Form):
    """Form for requesting company verification"""
    business_certificate = forms.FileField(
        label=_('Business Registration Certificate'),
        help_text=_('Upload a copy of your business registration certificate')
    )
    tin_certificate = forms.FileField(
        label=_('TIN Certificate'),
        required=False,
        help_text=_('Upload a copy of your TIN certificate (optional)')
    )
    verification_notes = forms.CharField(
        label=_('Additional Notes'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': _('Any additional information to support your verification')}),
    )
