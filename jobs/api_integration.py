import requests
import logging
import time
import json
from abc import ABC, abstractmethod
from django.utils import timezone
from django.db import transaction
from .models import Job, Company, ApiConfiguration, ApiRequestLog, Industry, Skill

logger = logging.getLogger(__name__)

class JobApiClient(ABC):
    """Abstract base class for all job API clients"""
    
    def __init__(self, api_config):
        self.api_config = api_config
        self.api_key = api_config.api_key
        self.api_secret = api_config.api_secret
        self.additional_params = api_config.additional_params
    
    @abstractmethod
    def fetch_jobs(self, **kwargs):
        """Fetch jobs from the API"""
        pass
    
    @abstractmethod
    def parse_job(self, job_data):
        """Parse job data from API into normalized format"""
        pass
    
    def _make_request(self, url, method='GET', params=None, headers=None, json_data=None, timeout=30):
        """Make HTTP request with error handling and logging"""
        params = params or {}
        headers = headers or {}
        start_time = time.time()
        
        # Create log entry
        log_entry = ApiRequestLog(
            api_config=self.api_config,
            endpoint=url,
            request_params=params
        )
        
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_data,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Update log entry
            log_entry.response_status = response.status_code
            log_entry.execution_time = execution_time
            
            # Check if response is successful
            response.raise_for_status()
            
            # Parse response data
            if response.content:
                response_data = response.json()
                # Truncate response data if it's too large for logging
                log_entry.response_data = self._truncate_response_data(response_data)
                return response_data
            return None
            
        except requests.RequestException as e:
            logger.error(f"API request error: {e}")
            log_entry.error_message = str(e)
            log_entry.response_status = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
            return None
        finally:
            # Save log entry
            log_entry.save()
            
            # Update API config request count
            self.api_config.request_count += 1
            self.api_config.last_fetch_date = timezone.now()
            self.api_config.save(update_fields=['request_count', 'last_fetch_date'])
    
    def _truncate_response_data(self, data, max_length=10000):
        """Truncate response data for logging"""
        data_str = json.dumps(data)
        if len(data_str) > max_length:
            return json.loads(f'{data_str[:max_length]}... [truncated]')
        return data


class LinkedInJobsClient(JobApiClient):
    """Client for LinkedIn Jobs API"""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(self, api_config):
        super().__init__(api_config)
        self.access_token = self._get_access_token()
    
    def _get_access_token(self):
        """Get OAuth2 access token"""
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(token_url, data=data, headers=headers)
        if response.ok:
            return response.json().get("access_token")
        else:
            logger.error(f"Failed to get LinkedIn access token: {response.text}")
            return None
    
    def fetch_jobs(self, **kwargs):
        """Fetch jobs from LinkedIn API"""
        if not self.access_token:
            logger.error("No LinkedIn access token available")
            return []
        
        # Get parameters from kwargs or use defaults
        country = kwargs.get('country', 'tz')  # Tanzania
        count = kwargs.get('count', 100)
        keywords = kwargs.get('keywords', '')
        
        # Endpoint for job search
        endpoint = f"{self.BASE_URL}/jobSearch"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        params = {
            "keywords": keywords,
            "locationName": country,
            "count": count
        }
        
        # Add any additional parameters from API config
        params.update(self.additional_params)
        
        # Make request
        response_data = self._make_request(endpoint, params=params, headers=headers)
        
        # Parse jobs
        jobs = []
        if response_data and 'elements' in response_data:
            for job_data in response_data['elements']:
                parsed_job = self.parse_job(job_data)
                if parsed_job:
                    jobs.append(parsed_job)
        
        return jobs
    
    def parse_job(self, job_data):
        """Parse LinkedIn job data"""
        try:
            # Extract basic job data
            job_id = job_data.get('jobId')
            title = job_data.get('title', '')
            company_name = job_data.get('companyName', '')
            location = job_data.get('locationName', '')
            description = job_data.get('description', '')
            apply_url = job_data.get('applyUrl', '')
            
            # Check for required fields
            if not all([job_id, title, company_name]):
                logger.warning(f"Missing required fields in LinkedIn job data: {job_data}")
                return None
            
            # Normalize job data
            return {
                'title': title,
                'company_name': company_name,
                'location': location,
                'description': description,
                'external_url': apply_url,
                'external_id': job_id,
                'source': 'linkedin'
            }
        except Exception as e:
            logger.error(f"Error parsing LinkedIn job: {e}")
            return None


class IndeedJobsClient(JobApiClient):
    """Client for Indeed Jobs API"""
    
    BASE_URL = "https://api.indeed.com/ads/apisearch"
    
    def fetch_jobs(self, **kwargs):
        """Fetch jobs from Indeed API"""
        # Get parameters from kwargs or use defaults
        country = kwargs.get('country', 'tz')  # Tanzania
        limit = kwargs.get('limit', 50)
        query = kwargs.get('query', '')
        
        params = {
            "publisher": self.api_key,
            "v": 2,  # API version
            "format": "json",
            "q": query,
            "l": country,
            "limit": limit,
            "sort": "date"
        }
        
        # Add any additional parameters from API config
        params.update(self.additional_params)
        
        # Make request
        response_data = self._make_request(self.BASE_URL, params=params)
        
        # Parse jobs
        jobs = []
        if response_data and 'results' in response_data:
            for job_data in response_data['results']:
                parsed_job = self.parse_job(job_data)
                if parsed_job:
                    jobs.append(parsed_job)
        
        return jobs
    
    def parse_job(self, job_data):
        """Parse Indeed job data"""
        try:
            # Extract basic job data
            job_id = job_data.get('jobkey')
            title = job_data.get('jobtitle', '')
            company_name = job_data.get('company', '')
            location = job_data.get('formattedLocation', '')
            description = job_data.get('snippet', '')
            url = job_data.get('url', '')
            
            # Check for required fields
            if not all([job_id, title, company_name]):
                logger.warning(f"Missing required fields in Indeed job data: {job_data}")
                return None
            
            # Normalize job data
            return {
                'title': title,
                'company_name': company_name,
                'location': location,
                'description': description,
                'external_url': url,
                'external_id': job_id,
                'source': 'indeed'
            }
        except Exception as e:
            logger.error(f"Error parsing Indeed job: {e}")
            return None


class AdzunaJobsClient(JobApiClient):
    """Client for Adzuna Jobs API"""
    
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"
    
    def fetch_jobs(self, **kwargs):
        """Fetch jobs from Adzuna API"""
        # Get parameters from kwargs or use defaults
        country = kwargs.get('country', 'tz').lower()  # Tanzania
        page = kwargs.get('page', 1)
        results_per_page = kwargs.get('results_per_page', 50)
        what = kwargs.get('what', '')  # Keywords
        
        # Endpoint for job search
        endpoint = f"{self.BASE_URL}/{country}/search/{page}"
        
        params = {
            "app_id": self.api_key,
            "app_key": self.api_secret,
            "results_per_page": results_per_page,
            "what": what,
            "content-type": "application/json"
        }
        
        # Add any additional parameters from API config
        params.update(self.additional_params)
        
        # Make request
        response_data = self._make_request(endpoint, params=params)
        
        # Parse jobs
        jobs = []
        if response_data and 'results' in response_data:
            for job_data in response_data['results']:
                parsed_job = self.parse_job(job_data)
                if parsed_job:
                    jobs.append(parsed_job)
        
        return jobs
    
    def parse_job(self, job_data):
        """Parse Adzuna job data"""
        try:
            # Extract basic job data
            job_id = job_data.get('id')
            title = job_data.get('title', '')
            company_name = job_data.get('company', {}).get('display_name', '')
            location = f"{job_data.get('location', {}).get('area', [''])[0]}"
            description = job_data.get('description', '')
            url = job_data.get('redirect_url', '')
            
            # Salary information
            salary_min = job_data.get('salary_min')
            salary_max = job_data.get('salary_max')
            
            # Check for required fields
            if not all([job_id, title]):
                logger.warning(f"Missing required fields in Adzuna job data: {job_data}")
                return None
            
            # Normalize job data
            job_data = {
                'title': title,
                'company_name': company_name,
                'location': location,
                'description': description,
                'external_url': url,
                'external_id': job_id,
                'source': 'adzuna'
            }
            
            # Add salary if available
            if salary_min:
                job_data['salary_min'] = salary_min
            if salary_max:
                job_data['salary_max'] = salary_max
            
            return job_data
        except Exception as e:
            logger.error(f"Error parsing Adzuna job: {e}")
            return None


class BrighterMondayJobsClient(JobApiClient):
    """Client for BrighterMonday Jobs API (Tanzania)"""
    
    BASE_URL = "https://www.brightermonday.co.tz/api/v1/jobs"
    
    def fetch_jobs(self, **kwargs):
        """Fetch jobs from BrighterMonday API"""
        # Get parameters from kwargs or use defaults
        limit = kwargs.get('limit', 50)
        offset = kwargs.get('offset', 0)
        
        params = {
            "limit": limit,
            "offset": offset
        }
        
        # Add any additional parameters from API config
        params.update(self.additional_params)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Make request
        response_data = self._make_request(self.BASE_URL, params=params, headers=headers)
        
        # Parse jobs
        jobs = []
        if response_data and 'data' in response_data:
            for job_data in response_data['data']:
                parsed_job = self.parse_job(job_data)
                if parsed_job:
                    jobs.append(parsed_job)
        
        return jobs
    
    def parse_job(self, job_data):
        """Parse BrighterMonday job data"""
        try:
            # Extract basic job data
            job_id = job_data.get('id')
            title = job_data.get('title', '')
            company_name = job_data.get('company_name', '')
            location = job_data.get('location', '')
            description = job_data.get('description', '')
            url = job_data.get('apply_url', '')
            
            # Job type and category
            job_type = job_data.get('job_type', '')
            
            # Check for required fields
            if not all([job_id, title, company_name]):
                logger.warning(f"Missing required fields in BrighterMonday job data: {job_data}")
                return None
            
            # Normalize job data
            job_data = {
                'title': title,
                'company_name': company_name,
                'location': location,
                'description': description,
                'external_url': url,
                'external_id': job_id,
                'source': 'brightermonday'
            }
            
            # Add job type if available
            if job_type:
                # Map BrighterMonday job types to our schema
                job_type_mapping = {
                    'Full Time': 'full_time',
                    'Part Time': 'part_time',
                    'Contract': 'contract',
                    'Internship': 'internship',
                    'Freelance': 'freelance'
                }
                job_data['job_type'] = job_type_mapping.get(job_type, '')
            
            return job_data
        except Exception as e:
            logger.error(f"Error parsing BrighterMonday job: {e}")
            return None


def get_api_client(api_name):
    """Get appropriate API client based on API name"""
    try:
        api_config = ApiConfiguration.objects.get(name=api_name, is_active=True)
        
        if api_name == 'linkedin':
            return LinkedInJobsClient(api_config)
        elif api_name == 'indeed':
            return IndeedJobsClient(api_config)
        elif api_name == 'adzuna':
            return AdzunaJobsClient(api_config)
        elif api_name == 'brightermonday':
            return BrighterMondayJobsClient(api_config)
        else:
            logger.error(f"Unknown API name: {api_name}")
            return None
    except ApiConfiguration.DoesNotExist:
        logger.error(f"No active configuration found for API: {api_name}")
        return None
    except Exception as e:
        logger.error(f"Error creating API client for {api_name}: {e}")
        return None


@transaction.atomic
def save_job_from_api(job_data):
    """Save job data from API to database with de-duplication"""
    # Check for duplicates by external_id and source
    external_id = job_data.get('external_id')
    source = job_data.get('source')
    
    # Skip if no external_id or source
    if not external_id or not source:
        logger.warning(f"Missing external_id or source in job data: {job_data}")
        return None, False
    
    # Check if job already exists
    existing_job = Job.objects.filter(external_id=external_id, source=source).first()
    
    if existing_job:
        # Update existing job
        existing_job.title = job_data.get('title', existing_job.title)
        existing_job.description = job_data.get('description', existing_job.description)
        existing_job.location = job_data.get('location', existing_job.location)
        existing_job.external_url = job_data.get('external_url', existing_job.external_url)
        
        # Update salary if provided
        if 'salary_min' in job_data:
            existing_job.salary_min = job_data.get('salary_min')
        if 'salary_max' in job_data:
            existing_job.salary_max = job_data.get('salary_max')
        
        # Update job type if provided
        if 'job_type' in job_data:
            existing_job.job_type = job_data.get('job_type')
        
        existing_job.save()
        return existing_job, False
    
    # Create company or get existing one
    company_name = job_data.get('company_name', 'Unknown Company')
    company, _ = Company.objects.get_or_create(
        name=company_name,
        defaults={
            'created_by_id': 1,  # Default admin user ID
            'is_verified': False
        }
    )
    
    # Create new job
    new_job = Job(
        title=job_data.get('title', ''),
        description=job_data.get('description', ''),
        company=company,
        location=job_data.get('location', ''),
        requirements=job_data.get('description', ''),  # Use description as requirements if no specific requirements
        external_id=external_id,
        external_url=job_data.get('external_url', ''),
        source=source,
        created_by_id=1,  # Default admin user ID
        posted_date=timezone.now(),
        application_deadline=timezone.now() + timezone.timedelta(days=30)  # Default 30 days
    )
    
    # Set job type if provided
    if 'job_type' in job_data:
        new_job.job_type = job_data.get('job_type')
    else:
        new_job.job_type = 'full_time'  # Default to full time
    
    # Set experience level
    new_job.experience_level = 'mid'  # Default to mid level
    
    # Set salary if provided
    if 'salary_min' in job_data:
        new_job.salary_min = job_data.get('salary_min')
    if 'salary_max' in job_data:
        new_job.salary_max = job_data.get('salary_max')
    
    # Save job
    new_job.save()
    
    # Extract and add skills (optional)
    if 'skills' in job_data and job_data['skills']:
        for skill_name in job_data['skills']:
            skill, _ = Skill.objects.get_or_create(name=skill_name)
            new_job.skills.add(skill)
    
    return new_job, True


def fetch_jobs_from_api(api_name, **kwargs):
    """Fetch jobs from specified API and save to database"""
    client = get_api_client(api_name)
    if not client:
        logger.error(f"Failed to get API client for {api_name}")
        return [], 0, 0
    
    # Fetch jobs
    jobs_data = client.fetch_jobs(**kwargs)
    
    # Save jobs to database
    created_count = 0
    updated_count = 0
    saved_jobs = []
    
    for job_data in jobs_data:
        job, created = save_job_from_api(job_data)
        if job:
            saved_jobs.append(job)
            if created:
                created_count += 1
            else:
                updated_count += 1
    
    # Update log with counts
    try:
        log = ApiRequestLog.objects.filter(api_config=client.api_config).order_by('-request_date').first()
        if log:
            log.jobs_fetched = len(jobs_data)
            log.jobs_created = created_count
            log.jobs_updated = updated_count
            log.save(update_fields=['jobs_fetched', 'jobs_created', 'jobs_updated'])
    except Exception as e:
        logger.error(f"Error updating API log: {e}")
    
    return saved_jobs, created_count, updated_count


def fetch_all_jobs():
    """Fetch jobs from all active APIs"""
    total_created = 0
    total_updated = 0
    all_saved_jobs = []
    
    # Get all active API configurations
    api_configs = ApiConfiguration.objects.filter(is_active=True)
    
    for config in api_configs:
        try:
            logger.info(f"Fetching jobs from {config.name}...")
            saved_jobs, created, updated = fetch_jobs_from_api(config.name)
            
            logger.info(f"Saved {len(saved_jobs)} jobs from {config.name}. Created: {created}, Updated: {updated}")
            
            total_created += created
            total_updated += updated
            all_saved_jobs.extend(saved_jobs)
        except Exception as e:
            logger.error(f"Error fetching jobs from {config.name}: {e}")
    
    logger.info(f"Completed fetching jobs from all APIs. Total Created: {total_created}, Total Updated: {total_updated}")
    return all_saved_jobs, total_created, total_updated
