from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.mail import send_mail

from .models import (
    Company, Job, JobApplication, SavedJob, JobSearchPreference,
    Industry, Skill, ApiConfiguration
)
from .forms import (
    CompanyForm, JobForm, JobApplicationForm, JobSearchForm, 
    JobSearchPreferenceForm, ApplicationStatusUpdateForm, CompanyVerificationRequestForm
)
from .api_integration import fetch_all_jobs, fetch_jobs_from_api
from .models import ApiRequestLog
import logging

logger = logging.getLogger(__name__)

# Home view for the jobs app
def jobs_home(request):
    public_jobs = Job.public_queryset().select_related('company', 'industry')
    featured_jobs = public_jobs.filter(is_featured=True)[:5]
    recent_jobs = public_jobs.order_by('-posted_date')[:10]
    job_count = public_jobs.count()
    
    # Group jobs by industry
    industry_public_filter = (
        Q(jobs__is_active=True)
        & (~(Q(jobs__source__isnull=True) | Q(jobs__source="") | Q(jobs__source="internal"))
           | ((Q(jobs__source__isnull=True) | Q(jobs__source="") | Q(jobs__source="internal")) & Q(jobs__company__is_verified=True)))
    )
    industries = (
        Industry.objects
        .annotate(job_count=Count('jobs', filter=industry_public_filter, distinct=True))
        .filter(job_count__gt=0)
        .order_by('-job_count')[:8]
    )
    
    context = {
        'featured_jobs': featured_jobs,
        'recent_jobs': recent_jobs,
        'job_count': job_count,
        'industries': industries,
    }
    return render(request, 'jobs/home.html', context)

# Job listing view
def job_list(request):
    jobs = Job.public_queryset().select_related('company', 'industry').prefetch_related('skills')
    search_form = JobSearchForm(request.GET)
    
    # Process search filters
    if search_form.is_valid():
        keywords = search_form.cleaned_data.get('keywords')
        location = search_form.cleaned_data.get('location')
        job_type = search_form.cleaned_data.get('job_type')
        experience_level = search_form.cleaned_data.get('experience_level')
        industry = search_form.cleaned_data.get('industry')
        salary_min = search_form.cleaned_data.get('salary_min')
        remote_only = search_form.cleaned_data.get('remote_only')
        is_featured = search_form.cleaned_data.get('is_featured')
        posted_since = search_form.cleaned_data.get('posted_since')
        
        # Apply filters
        if keywords:
            jobs = jobs.filter(
                Q(title__icontains=keywords) | 
                Q(description__icontains=keywords) | 
                Q(company__name__icontains=keywords) |
                Q(skills__name__icontains=keywords)
            ).distinct()
        
        if location:
            jobs = jobs.filter(location__icontains=location)
        
        if job_type:
            jobs = jobs.filter(job_type__in=job_type)
        
        if experience_level:
            jobs = jobs.filter(experience_level__in=experience_level)
        
        if industry:
            jobs = jobs.filter(industry=industry)
        
        if salary_min:
            jobs = jobs.filter(salary_min__gte=salary_min)
        
        if remote_only:
            jobs = jobs.filter(is_remote=True)
        
        if is_featured:
            jobs = jobs.filter(is_featured=True)
        
        if posted_since:
            days = int(posted_since)
            since_date = timezone.now() - timezone.timedelta(days=days)
            jobs = jobs.filter(posted_date__gte=since_date)
    
    # Pagination
    paginator = Paginator(jobs.order_by('-is_featured', '-posted_date'), 10)  # 10 jobs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get industries and job types for sidebar filters
    industry_public_filter = (
        Q(jobs__is_active=True)
        & (~(Q(jobs__source__isnull=True) | Q(jobs__source="") | Q(jobs__source="internal"))
           | ((Q(jobs__source__isnull=True) | Q(jobs__source="") | Q(jobs__source="internal")) & Q(jobs__company__is_verified=True)))
    )
    industries = Industry.objects.annotate(job_count=Count('jobs', filter=industry_public_filter, distinct=True)).filter(job_count__gt=0)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'industries': industries,
        'total_jobs': jobs.count(),
        'today': timezone.now(),
    }
    return render(request, 'jobs/job_list.html', context)

# Job detail view
def job_detail(request, job_id):
    job_qs = Job.objects.select_related('company', 'industry').prefetch_related('skills')
    job = get_object_or_404(job_qs, id=job_id)
    is_owner_or_admin = request.user.is_authenticated and (job.created_by_id == request.user.id or request.user.is_superuser)

    # Only show public jobs to everyone; owners/admins can always view
    if not job.is_public and not is_owner_or_admin:
        raise Http404(_('Job not available'))
    
    # Update view count only for active jobs
    if job.is_active:
        job.views_count += 1
        job.save(update_fields=['views_count'])
    
    # Check if user has already applied
    user_has_applied = False
    user_has_saved = False
    
    if request.user.is_authenticated:
        user_has_applied = JobApplication.objects.filter(job=job, applicant=request.user).exists()
        user_has_saved = SavedJob.objects.filter(job=job, user=request.user).exists()
    
    # Get similar jobs (only public listings)
    location_hint = job.location.split(',')[0] if job.location else ''
    similar_jobs = Job.public_queryset().filter(
        Q(industry=job.industry) | 
        Q(job_type=job.job_type) |
        Q(location__icontains=location_hint)
    ).exclude(id=job.id)[:5]
    
    context = {
        'job': job,
        'user_has_applied': user_has_applied,
        'user_has_saved': user_has_saved,
        'similar_jobs': similar_jobs,
        'application_form': JobApplicationForm() if request.user.is_authenticated and not user_has_applied else None,
        'is_owner_or_admin': is_owner_or_admin,
        'visibility_label': job.visibility_label,
    }
    return render(request, 'jobs/job_detail.html', context)

# Apply for job view
@login_required
@csrf_protect
def apply_for_job(request, job_id):
    job = get_object_or_404(Job.objects.select_related('company'), id=job_id)
    is_owner_or_admin = request.user.is_authenticated and (job.created_by_id == request.user.id or request.user.is_superuser)

    if (not job.is_public or not job.is_active) and not is_owner_or_admin:
        raise Http404(_('Job not available'))
    
    # Check if application deadline has passed
    if job.is_expired():
        messages.error(request, _('The application deadline for this job has passed.'))
        return redirect('jobs:job_detail', job_id=job.id)
    
    # Check if user already applied
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, _('You have already applied for this job.'))
        return redirect('jobs:job_detail', job_id=job.id)
    
    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES, job=job, user=request.user)
        if form.is_valid():
            application = form.save()
            
            # Send email notification to employer
            if job.company.email:
                subject = _('New Application for: {0}').format(job.title)
                message = _('''
                Hello {0},
                
                A new application has been submitted for your job posting: {1}
                
                Applicant: {2}
                
                You can review this application in your employer dashboard.
                
                Best regards,
                ChuoMarket Jobs Team
                ''').format(job.company.name, job.title, request.user.get_full_name() or request.user.username)
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [job.company.email],
                    fail_silently=True,
                )
            
            messages.success(request, _('Your application has been submitted successfully!'))
            return redirect('jobs:application_submitted', job_id=job.id)
    else:
        form = JobApplicationForm(job=job, user=request.user)
    
    context = {
        'form': form,
        'job': job,
    }
    return render(request, 'jobs/apply_for_job.html', context)

# Application submitted view
@login_required
def application_submitted(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/application_submitted.html', {'job': job})

# Save/bookmark job view
@login_required
@require_POST
def save_job(request, job_id):
    job = get_object_or_404(Job.objects.select_related('company'), id=job_id)
    is_owner_or_admin = request.user.is_authenticated and (job.created_by_id == request.user.id or request.user.is_superuser)

    if (not job.is_public or not job.is_active) and not is_owner_or_admin:
        raise Http404(_('Job not available'))
    saved_job = SavedJob.objects.filter(job=job, user=request.user).first()
    
    if saved_job:
        # If job was already saved, remove it
        saved_job.delete()
        created = False
        messages.success(request, _('Job removed from your bookmarks.'))
    else:
        # If job wasn't saved, save it
        SavedJob.objects.create(job=job, user=request.user)
        created = True
        messages.success(request, _('Job saved to your bookmarks.'))
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'created': created})
    return redirect('jobs:job_detail', job_id=job.id)

# Remove saved job view
@login_required
@require_POST
def remove_saved_job(request, job_id):
    job = get_object_or_404(Job.objects.select_related('company'), id=job_id)
    is_owner_or_admin = request.user.is_authenticated and (job.created_by_id == request.user.id or request.user.is_superuser)

    if (not job.is_public or not job.is_active) and not is_owner_or_admin:
        raise Http404(_('Job not available'))
    SavedJob.objects.filter(job=job, user=request.user).delete()
    
    messages.success(request, _('Job removed from your bookmarks.'))
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect('jobs:saved_jobs')

# User's saved jobs view
@login_required
def saved_jobs(request):
    saved_jobs = SavedJob.objects.filter(user=request.user).select_related('job', 'job__company').order_by('-saved_date')
    
    # Pagination
    paginator = Paginator(saved_jobs, 10)  # 10 saved jobs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'jobs/saved_jobs.html', context)

# User's job applications view
@login_required
def my_applications(request):
    applications = JobApplication.objects.filter(applicant=request.user).select_related('job', 'job__company').order_by('-applied_date')
    
    # Pagination
    paginator = Paginator(applications, 10)  # 10 applications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'jobs/my_applications.html', context)

# Company views
@login_required
def my_companies(request):
    companies = Company.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'jobs/my_companies.html', {'companies': companies})

@login_required
def create_company(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save(commit=False)
            company.created_by = request.user
            company.save()
            messages.success(request, _('Company created successfully.'))
            return redirect('jobs:my_companies')
    else:
        form = CompanyForm()
    
    return render(request, 'jobs/company_form.html', {'form': form, 'is_create': True})

@login_required
def edit_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Check if user is the owner
    if company.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to edit this company.'))
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, _('Company updated successfully.'))
            return redirect('jobs:my_companies')
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'jobs/company_form.html', {'form': form, 'company': company, 'is_create': False})

@login_required
def delete_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Check if user is the owner
    if company.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to delete this company.'))
    
    if request.method == 'POST':
        company.delete()
        messages.success(request, _('Company deleted successfully.'))
        return redirect('jobs:my_companies')
    
    return render(request, 'jobs/confirm_delete.html', {'company': company})

@login_required
def company_dashboard(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Check if user is the owner
    if company.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to view this company dashboard.'))
    
    # Get company jobs
    jobs = Job.objects.filter(company=company).order_by('-posted_date')
    
    # Get application statistics
    total_applications = JobApplication.objects.filter(job__company=company).count()
    
    # Applications by status
    applications_by_status = JobApplication.objects.filter(job__company=company).values('status').annotate(count=Count('id'))
    
    context = {
        'company': company,
        'jobs': jobs,
        'total_applications': total_applications,
        'applications_by_status': applications_by_status,
    }
    return render(request, 'jobs/company_dashboard.html', context)

# Job CRUD views
@login_required
def create_job(request):
    user_companies = Company.objects.filter(created_by=request.user)
    has_verified_company = user_companies.filter(is_verified=True).exists()
    has_companies = user_companies.exists()

    if request.method == 'POST':
        form = JobForm(request.POST, user=request.user)
        if form.is_valid():
            job = form.save(commit=False)
            if not job.source:
                job.source = 'internal'
            job.save()
            form.save_m2m()

            if job.is_public:
                messages.success(request, _('Job posted successfully and is live.'))
            else:
                messages.info(request, _('Job saved but will stay hidden until your company is verified.'))
            return redirect('jobs:my_jobs')
    else:
        form = JobForm(user=request.user)
    
    return render(
        request,
        'jobs/job_form.html',
        {
            'form': form,
            'is_create': True,
            'has_verified_company': has_verified_company,
            'has_companies': has_companies,
            'verified_companies': user_companies.filter(is_verified=True),
            'unverified_companies': user_companies.filter(is_verified=False),
        },
    )

@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the owner
    if job.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to edit this job.'))
    user_companies = Company.objects.filter(created_by=request.user)
    has_verified_company = user_companies.filter(is_verified=True).exists()
    has_companies = user_companies.exists()
    
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Job updated successfully.'))
            return redirect('jobs:my_jobs')
    else:
        form = JobForm(instance=job, user=request.user)
    
    return render(
        request,
        'jobs/job_form.html',
        {
            'form': form,
            'job': job,
            'is_create': False,
            'has_verified_company': has_verified_company,
            'has_companies': has_companies,
            'verified_companies': user_companies.filter(is_verified=True),
            'unverified_companies': user_companies.filter(is_verified=False),
            'is_public': job.is_public,
        },
    )

@login_required
def delete_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the owner
    if job.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to delete this job.'))
    
    if request.method == 'POST':
        job.delete()
        messages.success(request, _('Job deleted successfully.'))
        return redirect('jobs:my_jobs')
    
    return render(request, 'jobs/confirm_delete.html', {'job': job})

@login_required
def my_jobs(request):
    jobs = Job.objects.filter(created_by=request.user).select_related('company').order_by('-posted_date')
    user_companies = Company.objects.filter(created_by=request.user)
    context = {
        'jobs': jobs,
        'has_verified_company': user_companies.filter(is_verified=True).exists(),
        'has_companies': user_companies.exists(),
        'verified_companies': user_companies.filter(is_verified=True),
        'unverified_companies': user_companies.filter(is_verified=False),
    }
    return render(request, 'jobs/my_jobs.html', context)

# Job applications management views
@login_required
def job_applications(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the owner
    if job.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to view applications for this job.'))
    
    applications = JobApplication.objects.filter(job=job).order_by('-applied_date')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)
    
    context = {
        'job': job,
        'applications': applications,
        'status_filter': status,
    }
    return render(request, 'jobs/job_applications.html', context)

@login_required
def application_detail(request, application_id):
    application = get_object_or_404(JobApplication, id=application_id)
    
    # Check if user is the employer or the applicant
    is_employer = application.job.created_by == request.user
    is_applicant = application.applicant == request.user
    
    if not (is_employer or is_applicant or request.user.is_superuser):
        return HttpResponseForbidden(_('You do not have permission to view this application.'))
    
    if request.method == 'POST' and is_employer:
        form = ApplicationStatusUpdateForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, _('Application status updated.'))
            
            # Send email notification to applicant
            subject = _('Your application status has been updated')
            message = _('''
            Hello {0},
            
            Your application for the position "{1}" at {2} has been updated.
            
            New status: {3}
            
            Please log in to your account to view more details.
            
            Best regards,
            ChuoMarket Jobs Team
            ''').format(
                application.applicant.get_full_name() or application.applicant.username,
                application.job.title,
                application.job.company.name,
                application.get_status_display()
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [application.applicant.email],
                fail_silently=True,
            )
            
            return redirect('jobs:application_detail', application_id=application.id)
    else:
        form = ApplicationStatusUpdateForm(instance=application) if is_employer else None
    
    context = {
        'application': application,
        'form': form,
        'is_employer': is_employer,
        'is_applicant': is_applicant,
    }
    return render(request, 'jobs/application_detail.html', context)

# Search preferences views
@login_required
def job_preferences(request):
    preference, created = JobSearchPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = JobSearchPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request, _('Job preferences updated successfully.'))
            return redirect('jobs:job_preferences')
    else:
        form = JobSearchPreferenceForm(instance=preference)
    
    context = {
        'form': form,
        'preference': preference,
    }
    return render(request, 'jobs/job_preferences.html', context)

# Company verification request view
@login_required
def request_company_verification(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Check if user is the owner
    if company.created_by != request.user:
        return HttpResponseForbidden(_('You do not have permission to request verification for this company.'))
    
    # Check if company is already verified
    if company.is_verified:
        messages.info(request, _('This company is already verified.'))
        return redirect('jobs:company_dashboard', company_id=company.id)
    
    if request.method == 'POST':
        form = CompanyVerificationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            # Save verification documents
            # In a real implementation, you would save these files
            # and create a verification request record
            
            # Send email to admin
            subject = _('New Company Verification Request: {0}').format(company.name)
            message = _('''
            A new company verification request has been submitted:
            
            Company: {0}
            Requested by: {1} ({2})
            
            Please review this request in the admin panel.
            ''').format(
                company.name,
                request.user.get_full_name() or request.user.username,
                request.user.email
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL], # You need to define this in settings
                fail_silently=True,
            )
            
            messages.success(request, _('Verification request submitted successfully. We will review your documents and update your company status.'))
            return redirect('jobs:company_dashboard', company_id=company.id)
    else:
        form = CompanyVerificationRequestForm()
    
    context = {
        'form': form,
        'company': company,
    }
    return render(request, 'jobs/request_verification.html', context)


# Maintenance endpoint: deactivate expired jobs and fetch new ones
def maintenance_update_jobs(request):
    """Endpoint to be pinged (e.g., every 6 hours) to deactivate expired jobs
    and fetch new jobs from configured APIs. Returns simple JSON success/failure.

    Security: requires a secret token. Provide it either via GET param `token`
    or the header `X-JOBS-MAINTENANCE-TOKEN`. The token should be set in
    Django settings as JOBS_MAINTENANCE_TOKEN.
    """
    # Check token
    token = request.GET.get('token') or request.headers.get('X-JOBS-MAINTENANCE-TOKEN')
    expected = getattr(settings, 'JOBS_MAINTENANCE_TOKEN', None)
    if not expected or token != expected:
        logger.warning('Unauthorized maintenance_update_jobs attempt')
        return JsonResponse({'status': 'failure', 'reason': 'unauthorized'}, status=403)

    try:
        now = timezone.now()
        # Deactivate jobs past application_deadline
        expired_qs = Job.objects.filter(is_active=True, application_deadline__lt=now)
        expired_count = expired_qs.update(is_active=False)

        # Optionally, ensure jobs manually marked inactive remain so
        inactive_count = Job.objects.filter(is_active=False).count()

        # Ensure there's at least one active API config (Ajira scraper doesn't need credentials)
        api_configs = ApiConfiguration.objects.filter(is_active=True)
        if not api_configs.exists():
            # Create a minimal Ajira config so fetch_all_jobs has something to call
            try:
                ApiConfiguration.objects.create(name='ajira', api_key='ajira-scraper', api_secret='', is_active=True)
                logger.info('Created fallback Ajira ApiConfiguration')
            except Exception:
                logger.exception('Failed to create fallback Ajira ApiConfiguration')
        # First attempt: generic fetch from all APIs
        saved_jobs, created_count, updated_count = fetch_all_jobs()

        details = {
            'expired_deactivated': expired_count,
            'inactive_total': inactive_count,
            'jobs_fetched': len(saved_jobs),
            'jobs_created': created_count,
            'jobs_updated': updated_count,
            'per_api': [],
        }

        # If no jobs were fetched, try fetching per active ApiConfiguration to surface errors and act as fallback
        if len(saved_jobs) == 0:
            api_configs = ApiConfiguration.objects.filter(is_active=True)
            for cfg in api_configs:
                api_result = {'api': cfg.name, 'created': 0, 'updated': 0, 'fetched': 0, 'error': None}
                try:
                    api_saved, api_created, api_updated = fetch_jobs_from_api(cfg.name)
                    api_result['created'] = api_created
                    api_result['updated'] = api_updated
                    api_result['fetched'] = len(api_saved)
                    # attempt to grab last ApiRequestLog for this config
                    last_log = ApiRequestLog.objects.filter(api_config=cfg).order_by('-request_date').first()
                    if last_log:
                        api_result['last_log'] = {
                            'endpoint': last_log.endpoint,
                            'response_status': last_log.response_status,
                            'jobs_fetched': last_log.jobs_fetched,
                            'jobs_created': last_log.jobs_created,
                            'error_message': last_log.error_message,
                        }
                except Exception as e:
                    logger.exception(f"Error fetching jobs from API {cfg.name}")
                    api_result['error'] = str(e)
                details['per_api'].append(api_result)

            # If there were no active ApiConfigurations or still zero results, try Ajira explicitly as a last resort
            if not api_configs.exists() or all(p['fetched'] == 0 for p in details['per_api']):
                try:
                    ajira_saved, ajira_created, ajira_updated = fetch_jobs_from_api('ajira')
                    details['ajira_fetched'] = len(ajira_saved)
                    details['ajira_created'] = ajira_created
                    details['ajira_updated'] = ajira_updated
                except Exception as e:
                    logger.exception('Error running fallback Ajira fetch')
                    details['ajira_error'] = str(e)

        response = {'status': 'success', **details}
        return JsonResponse(response)
    except Exception as e:
        logger.exception('Error running maintenance_update_jobs')
        return JsonResponse({'status': 'failure', 'reason': str(e)}, status=500)
