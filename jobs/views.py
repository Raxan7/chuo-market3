from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse
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

# Home view for the jobs app
def jobs_home(request):
    featured_jobs = Job.objects.filter(is_active=True, is_featured=True)[:5]
    recent_jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:10]
    job_count = Job.objects.filter(is_active=True).count()
    
    # Group jobs by industry
    industries = Industry.objects.annotate(job_count=Count('jobs')).filter(job_count__gt=0).order_by('-job_count')[:8]
    
    context = {
        'featured_jobs': featured_jobs,
        'recent_jobs': recent_jobs,
        'job_count': job_count,
        'industries': industries,
    }
    return render(request, 'jobs/home.html', context)

# Job listing view
def job_list(request):
    jobs = Job.objects.filter(is_active=True)
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
    industries = Industry.objects.annotate(job_count=Count('jobs')).filter(job_count__gt=0)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'industries': industries,
        'total_jobs': jobs.count(),
    }
    return render(request, 'jobs/job_list.html', context)

# Job detail view
def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    # Update view count
    job.views_count += 1
    job.save(update_fields=['views_count'])
    
    # Check if user has already applied
    user_has_applied = False
    user_has_saved = False
    
    if request.user.is_authenticated:
        user_has_applied = JobApplication.objects.filter(job=job, applicant=request.user).exists()
        user_has_saved = SavedJob.objects.filter(job=job, user=request.user).exists()
    
    # Get similar jobs
    similar_jobs = Job.objects.filter(
        Q(industry=job.industry) | 
        Q(job_type=job.job_type) |
        Q(location__icontains=job.location.split(',')[0])
    ).exclude(id=job.id).filter(is_active=True)[:5]
    
    context = {
        'job': job,
        'user_has_applied': user_has_applied,
        'user_has_saved': user_has_saved,
        'similar_jobs': similar_jobs,
        'application_form': JobApplicationForm() if request.user.is_authenticated and not user_has_applied else None,
    }
    return render(request, 'jobs/job_detail.html', context)

# Apply for job view
@login_required
@csrf_protect
def apply_for_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
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
    job = get_object_or_404(Job, id=job_id, is_active=True)
    saved_job, created = SavedJob.objects.get_or_create(job=job, user=request.user)
    
    if created:
        messages.success(request, _('Job saved to your bookmarks.'))
    else:
        messages.info(request, _('This job is already in your bookmarks.'))
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'created': created})
    return redirect('jobs:job_detail', job_id=job.id)

# Remove saved job view
@login_required
@require_POST
def remove_saved_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
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
    if request.method == 'POST':
        form = JobForm(request.POST, user=request.user)
        if form.is_valid():
            job = form.save()
            messages.success(request, _('Job posted successfully.'))
            return redirect('jobs:my_jobs')
    else:
        form = JobForm(user=request.user)
    
    # If user has no companies, redirect to create company page
    if not Company.objects.filter(created_by=request.user).exists():
        messages.info(request, _('You need to create a company before posting jobs.'))
        return redirect('jobs:create_company')
    
    return render(request, 'jobs/job_form.html', {'form': form, 'is_create': True})

@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the owner
    if job.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to edit this job.'))
    
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Job updated successfully.'))
            return redirect('jobs:my_jobs')
    else:
        form = JobForm(instance=job, user=request.user)
    
    return render(request, 'jobs/job_form.html', {'form': form, 'job': job, 'is_create': False})

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
    jobs = Job.objects.filter(created_by=request.user).order_by('-posted_date')
    return render(request, 'jobs/my_jobs.html', {'jobs': jobs})

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
