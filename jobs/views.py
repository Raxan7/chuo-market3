from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse, Http404, FileResponse
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
from core.emailing import send_transactional_email

from .models import (
    Company, CompanyVerificationRequest, Job, JobApplication, SavedJob, JobSearchPreference,
    Industry, Skill, ApiConfiguration
)
from .forms import (
    CompanyForm, JobForm, JobApplicationForm, JobSearchForm, 
    JobSearchPreferenceForm, ApplicationStatusUpdateForm, CompanyVerificationRequestForm
)
from .api_integration import fetch_all_jobs, fetch_jobs_from_api
from .models import ApiRequestLog
import logging
import uuid

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
    
    # Apply ordering
    jobs = jobs.order_by('-is_featured', '-posted_date')
    
    # Offset-based pagination for infinite scroll:
    #   - Initial page load: load all jobs
    #   - AJAX scroll loads: 10 jobs  (offset=N, limit=10)
    total_jobs_count = jobs.count()
    offset = int(request.GET.get('offset', 0))
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        limit = int(request.GET.get('limit', 10))
    else:
        limit = total_jobs_count or 1
    page_jobs = jobs[offset:offset + limit]
    has_next = (offset + limit) < total_jobs_count
    next_offset = offset + limit if has_next else None
    
    # Get industries and job types for sidebar filters
    industry_public_filter = (
        Q(jobs__is_active=True)
        & (~(Q(jobs__source__isnull=True) | Q(jobs__source="") | Q(jobs__source="internal"))
           | ((Q(jobs__source__isnull=True) | Q(jobs__source="") | Q(jobs__source="internal")) & Q(jobs__company__is_verified=True)))
    )
    industries = Industry.objects.annotate(job_count=Count('jobs', filter=industry_public_filter, distinct=True)).filter(job_count__gt=0)
    
    # AJAX request: return only the job items as HTML fragment for infinite scroll
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        from django.middleware.csrf import get_token
        list_html = render_to_string('jobs/_job_items.html', {
            'jobs': page_jobs,
            'user': request.user,
            'today': timezone.now(),
            'csrf_token': get_token(request),
        })
        grid_html = render_to_string('jobs/_job_grid_items.html', {
            'jobs': page_jobs,
            'user': request.user,
            'today': timezone.now(),
        })
        return JsonResponse({
            'list_html': list_html,
            'grid_html': grid_html,
            'has_next': has_next,
            'next_offset': next_offset,
            'total': total_jobs_count,
        })
    
    context = {
        'jobs': page_jobs,
        'total_jobs': total_jobs_count,
        'has_next': has_next,
        'next_offset': next_offset,
        'search_form': search_form,
        'industries': industries,
        'today': timezone.now(),
        'jobs_listing_json_ld': {
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            'name': 'Jobs in Tanzania',
            'description': 'Browse job opportunities, internships, and graduate roles in Tanzania.',
        },
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
        'application_form': JobApplicationForm() if request.user.is_authenticated and job.is_public and job.is_active and not job.is_expired() and not user_has_applied else None,
        'is_owner_or_admin': is_owner_or_admin,
        'visibility_label': job.visibility_label,
    }
    from django.utils.html import strip_tags
    from django.template.defaultfilters import truncatechars
    from django.conf import settings
    domain = getattr(settings, 'SITE_DOMAIN', 'chuosmart.com')
    base_url = f"https://{domain}"
    job_url = request.build_absolute_uri()
    job_json_ld = {
        '@context': 'https://schema.org',
        '@type': 'JobPosting',
        'title': job.title or '',
        'description': truncatechars(strip_tags(job.description or ''), 400),
        'datePosted': job.posted_date.isoformat() if job.posted_date else None,
        'employmentType': job.get_job_type_display(),
        'hiringOrganization': {
            '@type': 'Organization',
            'name': job.company.name if job.company else '',
            'sameAs': job.company.website if getattr(job.company, 'website', None) else base_url,
        },
        'jobLocation': {
            '@type': 'Place',
            'address': {
                '@type': 'PostalAddress',
                'addressLocality': job.location or '',
                'addressCountry': 'TZ',
            },
        },
        'url': job_url,
    }
    job_breadcrumb_json_ld = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {
                '@type': 'ListItem',
                'position': 1,
                'name': 'Home',
                'item': f"{base_url}/",
            },
            {
                '@type': 'ListItem',
                'position': 2,
                'name': 'Jobs',
                'item': f"{base_url}{reverse('jobs:job_list')}",
            },
            {
                '@type': 'ListItem',
                'position': 3,
                'name': job.title or '',
                'item': job_url,
            },
        ],
    }
    context['job_json_ld'] = job_json_ld
    context['job_breadcrumb_json_ld'] = job_breadcrumb_json_ld

    if request.user.is_authenticated and not user_has_applied:
        try:
            from .recommendations import get_recommendations
            context['course_recommendations'] = get_recommendations(job)
        except Exception as e:
            logger.error('Failed to get course recommendations for job %s: %s', job.id, e)

    return render(request, 'jobs/job_detail.html', context)

# Apply for job view
@login_required
@csrf_protect
def apply_for_job(request, job_id):
    job = get_object_or_404(Job.objects.select_related('company', 'industry'), id=job_id)

    if not job.is_public or not job.is_active or job.is_expired():
        raise Http404(_('Job not available'))
    if job.created_by_id == request.user.id:
        messages.info(request, _('You cannot apply to your own job posting.'))
        return redirect('jobs:job_detail', job_id=job.id)

    if job.job_posting_type == 'external':
        if job.external_url:
            return redirect(job.external_url)
        messages.error(request, _('This external job is missing its application link.'))
        return redirect('jobs:job_detail', job_id=job.id)

    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, _('You have already applied for this job.'))
        return redirect('jobs:job_detail', job_id=job.id)

    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES, job=job, user=request.user)
        if form.is_valid():
            application = form.save()
            if job.company and job.company.email:
                send_transactional_email(
                    subject=_('New Application for: {0}').format(job.title),
                    message=_(
                        'Hello {company},\n\nA new application has been submitted for "{job}".\n\n'
                        'Applicant: {applicant}\nContact: {phone}\n\n'
                        'Log in to ChuoSmart to review the application.'
                    ).format(
                        company=job.company.name,
                        job=job.title,
                        applicant=request.user.get_full_name() or request.user.username,
                        phone=application.phone_number or request.user.email,
                    ),
                    recipients=[job.company.email],
                )
            messages.success(request, _('Your application has been submitted successfully!'))
            return redirect('jobs:application_submitted', job_id=job.id)
    else:
        form = JobApplicationForm(job=job, user=request.user)

    recommendations = []
    try:
        from .recommendations import get_recommendations
        recommendations = get_recommendations(job)
    except Exception as exc:
        logger.error('Failed to get course recommendations for job %s: %s', job.id, exc)

    return render(request, 'jobs/job_apply.html', {
        'form': form,
        'job': job,
        'course_recommendations': recommendations,
    })

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
    if company.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to view this company dashboard.'))

    jobs = Job.objects.filter(company=company).order_by('-posted_date')
    applications = JobApplication.objects.filter(job__company=company).select_related('job', 'applicant')
    applications_by_status = applications.values('status').annotate(count=Count('id')).order_by('status')
    pending_verification = company.verification_requests.filter(status='pending').first()

    return render(request, 'jobs/company_dashboard.html', {
        'company': company,
        'jobs': jobs,
        'active_jobs': jobs.filter(is_active=True),
        'total_applications': applications.count(),
        'recent_applications': applications.order_by('-applied_date')[:8],
        'applications_by_status': applications_by_status,
        'pending_verification': pending_verification,
    })


def company_detail(request, company_id):
    company = get_object_or_404(Company.objects.select_related('created_by'), id=company_id)
    owner_or_admin = request.user.is_authenticated and (
        request.user.is_superuser or company.created_by_id == request.user.id
    )
    if not company.is_verified and not owner_or_admin:
        raise Http404(_('Company not available'))
    jobs = Job.public_queryset().filter(company=company).select_related('industry').order_by('-posted_date')
    return render(request, 'jobs/company_detail.html', {'company': company, 'jobs': jobs})


@login_required
def private_verification_document(request, file_path):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden(_('Only staff can access verification documents.'))
    normalized = file_path.replace('\\', '/').lstrip('/')
    if '..' in normalized.split('/'):
        raise Http404()
    request_exists = CompanyVerificationRequest.objects.filter(
        Q(business_certificate=normalized) | Q(tin_certificate=normalized)
    ).exists()
    if not request_exists:
        raise Http404()
    from .storage import private_verification_storage
    try:
        handle = private_verification_storage.open(normalized, 'rb')
    except FileNotFoundError:
        raise Http404()
    return FileResponse(handle, as_attachment=False, filename=normalized.rsplit('/', 1)[-1])

# Job CRUD views
@login_required
def create_job(request):
    initial = {}
    requested_company_id = request.GET.get('company')
    if requested_company_id:
        company = Company.objects.filter(id=requested_company_id, created_by=request.user).first()
        if company:
            initial['company'] = company

    if request.method == 'POST':
        form = JobForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                # Job persistence must be all-or-nothing. Email/newsletter work is
                # handled separately by failure-isolated post-commit callbacks.
                with transaction.atomic():
                    job = form.save(commit=False)
                    if not job.source:
                        job.source = 'internal'
                    job.created_by = request.user
                    job.save()
                    form.save_m2m()
            except Exception:
                incident_ref = uuid.uuid4().hex[:10]
                logger.exception(
                    'Job creation failed ref=%s user_id=%s company_id=%s',
                    incident_ref,
                    request.user.pk,
                    request.POST.get('company') or None,
                )
                form.add_error(
                    None,
                    _('We could not save this job right now. Please try again. Reference: {0}').format(incident_ref),
                )
            else:
                try:
                    is_public = job.is_public
                    visibility_label = job.visibility_label
                except Exception:
                    # The database write already succeeded. A visibility lookup must
                    # not turn that success into a 500 response.
                    logger.exception('Visibility lookup failed after creating job_id=%s', job.pk)
                    is_public = False
                    visibility_label = _('Saved')
                logger.info(
                    'Job created successfully job_id=%s user_id=%s company_id=%s public=%s',
                    job.pk,
                    request.user.pk,
                    job.company_id,
                    is_public,
                )
                if is_public:
                    messages.success(request, _('Job posted successfully and is live.'))
                else:
                    messages.info(request, _(
                        'Job saved successfully. Current visibility: {0}. Complete employer verification to publish it.'
                    ).format(visibility_label))
                return redirect('jobs:my_jobs')
        else:
            logger.warning(
                'Job form rejected user_id=%s fields=%s errors=%s',
                request.user.pk,
                sorted(request.POST.keys()),
                {field: [str(error) for error in errors] for field, errors in form.errors.items()},
            )
    else:
        form = JobForm(user=request.user, initial=initial)

    return render(request, 'jobs/job_form.html', {'form': form, 'is_create': True})

@login_required
def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if job.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to edit this job.'))

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    job = form.save()
            except Exception:
                incident_ref = uuid.uuid4().hex[:10]
                logger.exception(
                    'Job update failed ref=%s job_id=%s user_id=%s',
                    incident_ref,
                    job.pk,
                    request.user.pk,
                )
                form.add_error(
                    None,
                    _('We could not save these job changes right now. Please try again. Reference: {0}').format(incident_ref),
                )
            else:
                try:
                    is_public = job.is_public
                    visibility_label = job.visibility_label
                except Exception:
                    logger.exception('Visibility lookup failed after updating job_id=%s', job.pk)
                    is_public = False
                    visibility_label = _('Saved')
                if is_public:
                    messages.success(request, _('Job updated successfully and is live.'))
                else:
                    messages.info(request, _('Job updated. Current visibility: {0}.').format(visibility_label))
                return redirect('jobs:my_jobs')
        else:
            logger.warning(
                'Job edit form rejected job_id=%s user_id=%s fields=%s errors=%s',
                job.pk,
                request.user.pk,
                sorted(request.POST.keys()),
                {field: [str(error) for error in errors] for field, errors in form.errors.items()},
            )
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
    if job.created_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_('You do not have permission to view applications for this job.'))

    applications = JobApplication.objects.filter(job=job).select_related('applicant').order_by('-applied_date')
    status = request.GET.get('status')
    valid_statuses = {choice[0] for choice in JobApplication._meta.get_field('status').choices}
    if status in valid_statuses:
        applications = applications.filter(status=status)
    else:
        status = ''

    return render(request, 'jobs/job_applications.html', {
        'job': job,
        'applications': applications,
        'status_filter': status,
        'status_choices': JobApplication._meta.get_field('status').choices,
    })

@login_required
def application_detail(request, application_id):
    application = get_object_or_404(
        JobApplication.objects.select_related('job', 'job__company', 'applicant'),
        id=application_id,
    )
    is_employer = application.job.created_by == request.user
    is_applicant = application.applicant == request.user
    if not (is_employer or is_applicant or request.user.is_superuser):
        return HttpResponseForbidden(_('You do not have permission to view this application.'))

    if request.method == 'POST' and (is_employer or request.user.is_superuser):
        form = ApplicationStatusUpdateForm(request.POST, instance=application)
        if form.is_valid():
            application = form.save()
            messages.success(request, _('Application status updated.'))
            if application.applicant.email:
                company_name = application.job.company.name if application.job.company else 'the employer'
                send_transactional_email(
                    subject=_('Your application status has been updated'),
                    message=_(
                        'Hello {name},\n\nYour application for "{job}" at {company} has been updated.\n\n'
                        'New status: {status}\n\nLog in to ChuoSmart to view your application.'
                    ).format(
                        name=application.applicant.get_full_name() or application.applicant.username,
                        job=application.job.title,
                        company=company_name,
                        status=application.get_status_display(),
                    ),
                    recipients=[application.applicant.email],
                )
            return redirect('jobs:application_detail', application_id=application.id)
    else:
        form = ApplicationStatusUpdateForm(instance=application) if (is_employer or request.user.is_superuser) else None

    return render(request, 'jobs/application_detail.html', {
        'application': application,
        'form': form,
        'is_employer': is_employer,
        'is_applicant': is_applicant,
    })

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
    if company.created_by != request.user:
        return HttpResponseForbidden(_('You do not have permission to request verification for this company.'))
    if company.is_verified:
        messages.info(request, _('This company is already verified.'))
        return redirect('jobs:company_dashboard', company_id=company.id)

    pending = company.verification_requests.filter(status='pending').first()
    if request.method == 'POST':
        if pending:
            messages.info(request, _('A verification request is already pending review.'))
            return redirect('jobs:company_dashboard', company_id=company.id)
        form = CompanyVerificationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.company = company
            verification.requested_by = request.user
            verification.save()
            send_transactional_email(
                subject=_('New Company Verification Request: {0}').format(company.name),
                message=_(
                    'A company verification request was submitted.\n\nCompany: {company}\nRequested by: {user} ({email})\n\nReview it in Django admin.'
                ).format(
                    company=company.name,
                    user=request.user.get_full_name() or request.user.username,
                    email=request.user.email,
                ),
                recipients=[settings.ADMIN_EMAIL],
            )
            messages.success(request, _('Verification request submitted. We will notify you after review.'))
            return redirect('jobs:company_dashboard', company_id=company.id)
    else:
        form = CompanyVerificationRequestForm()

    return render(request, 'jobs/request_verification.html', {
        'form': form,
        'company': company,
        'pending_verification': pending,
    })


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
