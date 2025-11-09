import requests
import logging
import time
import json
from abc import ABC, abstractmethod
from django.utils import timezone
from django.db import transaction
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import warnings
from urllib3.exceptions import InsecureRequestWarning
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
        elif api_name == 'ajira':
            # Prefer GraphQL client when available; fallback to HTML scraper
            try:
                return AjiraGraphQLClient(api_config)
            except Exception:
                return AjiraJobsClient(api_config)
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
        requirements=job_data.get('requirements', job_data.get('description', '')),  # Use specific requirements if available
        responsibilities=job_data.get('responsibilities', ''),  # Use responsibilities if available
        external_id=external_id,
        external_url=job_data.get('external_url', ''),
        source=source,
        created_by_id=1,  # Default admin user ID
        posted_date=timezone.now(),
        application_deadline=job_data.get('application_deadline', timezone.now() + timezone.timedelta(days=30))  # Use provided deadline or default
    )
    
    # Set job type if provided
    if 'job_type' in job_data:
        new_job.job_type = job_data.get('job_type')
    else:
        new_job.job_type = 'full_time'  # Default to full time
    
    # Set experience level if provided
    if 'experience_level' in job_data:
        new_job.experience_level = job_data.get('experience_level')
    else:
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


class AjiraJobsClient(JobApiClient):
    """Client for scraping jobs from Ajira Portal Tanzania"""
    
    BASE_URL = "https://portal.ajira.go.tz/"
    
    def __init__(self, api_config):
        super().__init__(api_config)
        # Suppress only the InsecureRequestWarning from urllib3
        warnings.simplefilter('ignore', InsecureRequestWarning)
    
    def fetch_jobs(self, **kwargs):
        """Fetch jobs from Ajira Portal Tanzania"""
        logger.info("Starting job scraping from Ajira Portal")
        
        jobs_data = []
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create log entry for the main page request
        log_entry = ApiRequestLog(
            api_config=self.api_config,
            endpoint=self.BASE_URL,
            request_params={}
        )
        try:
            response = requests.get(self.BASE_URL, headers=headers, verify=False)
            log_entry.response_status = response.status_code
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Step 1: Collect candidate links (categories or direct job links). Be permissive - site structure may change.
            candidate_links = set()
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                text = (a.get_text(' ', strip=True) or '').lower()
                if not href or href == '#':
                    continue
                href_l = href.lower()
                # look for patterns that indicate category listing or job details
                if any(p in href_l for p in ['/advert', '/advert/index', '/advertisement', '/vacancy', '/job', '/jobs']) or 'more details' in text or 'view details' in text:
                    # normalize relative urls
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = self.BASE_URL.rstrip('/') + href
                        else:
                            href = self.BASE_URL.rstrip('/') + '/' + href.lstrip('/')
                    candidate_links.add(href)

            candidate_links = list(candidate_links)
            logger.info(f"Found {len(candidate_links)} candidate links on Ajira Portal")

            # Step 2: Scrape jobs from each candidate link (either category pages or direct job pages)
            for cat_link in candidate_links:
                logger.info(f"Scraping candidate link: {cat_link}")
                try:
                    cat_resp = requests.get(cat_link, headers=headers, verify=False, timeout=20)
                    cat_resp.raise_for_status()
                    cat_soup = BeautifulSoup(cat_resp.text, 'html.parser')

                    # Prefer table rows if present (older layout), else look for lists or direct job anchors
                    tables = cat_soup.find_all('table')
                    if tables:
                        table = tables[0]
                        rows = table.find_all('tr')
                        for row in rows[1:]:  # skip header
                            cells = row.find_all('td')
                            if not cells:
                                continue
                            summary_full = cells[0].get_text(strip=True)
                            closing_date = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                            more_link = row.find('a', string=lambda s: s and 'more details' in s.lower())
                            job_url = ''
                            if more_link and more_link.get('href'):
                                job_url = more_link.get('href')
                                if not job_url.startswith('http'):
                                    if job_url.startswith('/'):
                                        job_url = self.BASE_URL.rstrip('/') + job_url
                                    else:
                                        job_url = self.BASE_URL.rstrip('/') + '/' + job_url.lstrip('/')
                            summary_clean = summary_full.replace('More Details', '').strip()
                            job_post = summary_clean
                            employer = ''
                            if 'employer:' in summary_clean.lower():
                                parts = summary_clean.split('Employer:')
                                job_post = parts[0].strip().rstrip(',')
                                employer = parts[1].strip().rstrip(',') if len(parts) > 1 else ''

                            # Fetch details if we have a job URL
                            job_title = ''
                            description = ''
                            requirements = ''
                            if job_url:
                                try:
                                    job_resp = requests.get(job_url, headers=headers, verify=False, timeout=20)
                                    job_resp.raise_for_status()
                                    job_soup = BeautifulSoup(job_resp.text, 'html.parser')
                                    title_tag = job_soup.find(['h1', 'h2']) or job_soup.find('title')
                                    if title_tag:
                                        job_title = title_tag.get_text(strip=True)
                                    desc_tag = job_soup.find('div', class_='panel-body') or job_soup.find('div', class_='job-desc') or job_soup.find('div', id='job-description')
                                    if desc_tag:
                                        description = desc_tag.get_text(' ', strip=True)
                                    else:
                                        p_tag = job_soup.find('p')
                                        if p_tag:
                                            description = p_tag.get_text(' ', strip=True)
                                    req_tag = job_soup.find(string=lambda s: s and 'requirement' in s.lower()) or job_soup.find('ul')
                                    if req_tag:
                                        if hasattr(req_tag, 'get_text'):
                                            requirements = req_tag.get_text(' ', strip=True)
                                        else:
                                            requirements = str(req_tag)
                                except Exception as e:
                                    logger.warning(f"Error fetching job details for {job_url}: {e}")

                            job_data = {
                                'title': job_title or job_post,
                                'employer': employer,
                                'closing_date_text': closing_date,
                                'description': description,
                                'requirements': requirements,
                                'job_url': job_url,
                                'external_id': job_url.split('/')[-1] if job_url else '',
                            }
                            normalized_job = self.parse_job(job_data)
                            if normalized_job:
                                jobs_data.append(normalized_job)
                            else:
                                logger.warning(f"Failed to normalize job data: {job_data}")
                    else:
                        # No table: look for anchors that look like job detail links and fetch them
                        anchors = []
                        for a in cat_soup.find_all('a', href=True):
                            href = a.get('href')
                            text = (a.get_text(' ', strip=True) or '').lower()
                            if not href or href == '#':
                                continue
                            if any(tok in href.lower() for tok in ['/job', '/jobs', '/vacancy', '/advert']) or 'more details' in text or 'view details' in text:
                                if not href.startswith('http'):
                                    if href.startswith('/'):
                                        href = self.BASE_URL.rstrip('/') + href
                                    else:
                                        href = self.BASE_URL.rstrip('/') + '/' + href.lstrip('/')
                                anchors.append(href)

                        anchors = list(dict.fromkeys(anchors))
                        for job_url in anchors:
                            job_title = ''
                            description = ''
                            requirements = ''
                            try:
                                job_resp = requests.get(job_url, headers=headers, verify=False, timeout=20)
                                job_resp.raise_for_status()
                                job_soup = BeautifulSoup(job_resp.text, 'html.parser')
                                title_tag = job_soup.find(['h1', 'h2']) or job_soup.find('title')
                                if title_tag:
                                    job_title = title_tag.get_text(strip=True)
                                desc_tag = job_soup.find('div', class_='panel-body') or job_soup.find('div', class_='job-desc')
                                if desc_tag:
                                    description = desc_tag.get_text(' ', strip=True)
                                else:
                                    p_tag = job_soup.find('p')
                                    if p_tag:
                                        description = p_tag.get_text(' ', strip=True)
                                req_tag = job_soup.find(string=lambda s: s and 'requirement' in s.lower()) or job_soup.find('ul')
                                if req_tag:
                                    if hasattr(req_tag, 'get_text'):
                                        requirements = req_tag.get_text(' ', strip=True)
                                    else:
                                        requirements = str(req_tag)
                            except Exception as e:
                                logger.warning(f"Error fetching fallback job details: {e}")
                            job_data = {
                                'title': job_title or '',
                                'employer': '',
                                'closing_date_text': '',
                                'description': description,
                                'requirements': requirements,
                                'job_url': job_url,
                                'external_id': job_url.split('/')[-1] if job_url else '',
                            }
                            normalized_job = self.parse_job(job_data)
                            if normalized_job:
                                jobs_data.append(normalized_job)
                            else:
                                logger.warning(f"Failed to normalize fallback job data: {job_data}")
                except Exception as e:
                    logger.error(f"Error fetching candidate page: {e}")
            log_entry.jobs_fetched = len(jobs_data)
            logger.info(f"Successfully scraped {len(jobs_data)} jobs from Ajira Portal")
        except Exception as e:
            logger.error(f"Error scraping Ajira Portal: {e}")
            log_entry.error_message = str(e)
            if not hasattr(log_entry, 'response_status') or log_entry.response_status is None:
                log_entry.response_status = 0
        finally:
            if log_entry.response_status is None:
                log_entry.response_status = 0
            log_entry.save()
            self.api_config.request_count += 1
            self.api_config.last_fetch_date = timezone.now()
            self.api_config.save(update_fields=['request_count', 'last_fetch_date'])
        return jobs_data

    def parse_job(self, job_data):
        """Parse job data from Ajira Portal into normalized format"""
        # Parse closing date
        closing_date = None
        closing_date_text = job_data.get('closing_date_text', '')
        try:
            date_formats = [
                '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', 
                '%d %b %Y', '%d %B %Y', '%B %d, %Y'
            ]
            for fmt in date_formats:
                try:
                    closing_date = datetime.strptime(closing_date_text, fmt)
                    break
                except ValueError:
                    continue
            if not closing_date:
                closing_date = timezone.now() + timezone.timedelta(days=30)
                logger.warning(f"Could not parse closing date: {closing_date_text}. Using default (30 days).")
        except Exception as e:
            logger.error(f"Error parsing closing date: {e}")
            closing_date = timezone.now() + timezone.timedelta(days=30)

        # Remove 'READ MORE' from description and requirements
        def clean_text(text):
            if not text:
                return ''
            return text.replace('READ MORE', '').strip()

        # Determine job type
        job_type = 'full_time'  # Default
        title_lower = job_data.get('title', '').lower()
        if 'part time' in title_lower or 'part-time' in title_lower:
            job_type = 'part_time'
        elif 'contract' in title_lower:
            job_type = 'contract'
        elif 'intern' in title_lower:
            job_type = 'internship'

        # Determine experience level
        experience_level = 'mid'  # Default
        if 'senior' in title_lower or 'experienced' in title_lower:
            experience_level = 'senior'
        elif 'junior' in title_lower or 'entry' in title_lower:
            experience_level = 'entry'
        elif 'manager' in title_lower or 'director' in title_lower or 'executive' in title_lower:
            experience_level = 'executive'

        # Make sure we have an external_id
        external_id = job_data.get('external_id', '')
        if not external_id:
            job_url = job_data.get('job_url', '')
            if job_url:
                external_id = job_url.split('/')[-1]
            if not external_id and job_data.get('title'):
                import hashlib
                external_id = hashlib.md5(job_data.get('title', '').encode()).hexdigest()

        # Ensure we have a company name
        company_name = job_data.get('employer', '')
        if not company_name:
            title = job_data.get('title', '')
            if 'Employer:' in title:
                parts = title.split('Employer:')
                if len(parts) > 1:
                    company_parts = parts[1].split('More Details')
                    company_name = company_parts[0].strip()
        if not company_name:
            company_name = 'Ajira Portal Tanzania'

        # Create a normalized job data structure
        normalized_data = {
            'title': job_data.get('title', ''),
            'description': clean_text(job_data.get('description', '')),
            'requirements': clean_text(job_data.get('requirements', '')),
            'responsibilities': '',  # Not available separately from description
            'location': 'Tanzania',  # Default location
            'job_type': job_type,
            'experience_level': experience_level,
            'application_deadline': closing_date,
            'external_url': job_data.get('job_url', ''),
            'external_id': external_id,
            'company_name': company_name,
            'source': 'ajira'  # Make sure this is always set
        }
        return normalized_data


class AjiraGraphQLClient(JobApiClient):
    """Client that queries Ajira's GraphQL backend directly (preferred over HTML scraping).

    This client is configurable via the ApiConfiguration record. The base URL used
    will be taken from api_config.additional_params.get('base_url') or default to
    'https://portal.ajira.go.tz'. The GraphQL endpoint is assumed to be <base>/graphql.
    """

    DEFAULT_BASE = "https://portal.ajira.go.tz"

    GET_VACANCIES_QUERY = '''
    query GetVacancies {
      getVacancies {
        id
        scheme {
          id
          codeNo
          emp { id name }
        }
        openDate
        closeDate
        noOfPost
        shortlistConfirmed
        vacancyStatus { isClosed daysClosedAgo statusText daysRemaining }
      }
    }
    '''

    def __init__(self, api_config):
        super().__init__(api_config)
        self.base_url = api_config.additional_params.get('base_url') or self.DEFAULT_BASE
        self.graphql_url = self.base_url.rstrip('/') + '/graphql'

    def _post_graphql(self, query, variables=None, headers=None, timeout=20):
        headers = headers or {}
        headers.setdefault('Content-Type', 'application/json')
        headers.setdefault('Accept', 'application/json')
        # Allow callers to specify UA/Origin in api_config.additional_params if needed
        ua = self.api_config.additional_params.get('user_agent')
        if ua:
            headers.setdefault('User-Agent', ua)

        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        # Use _make_request to get ApiRequestLog wiring and request counting
        return self._make_request(self.graphql_url, method='POST', json_data=payload, headers=headers, timeout=timeout)

    def fetch_jobs(self, **kwargs):
        """Fetch vacancies via GraphQL and map to normalized job dicts."""
        response = self._post_graphql(self.GET_VACANCIES_QUERY)
        jobs = []
        try:
            if not response:
                return jobs
            data = response.get('data') or response
            vacancies = data.get('getVacancies') if isinstance(data, dict) else None
            if not vacancies:
                return jobs

            for vac in vacancies:
                mapped = self._map_vacancy_to_job(vac)
                if mapped:
                    jobs.append(mapped)
        except Exception as e:
            logger.error(f"Error parsing GraphQL vacancies response: {e}")
        return jobs

    def _map_vacancy_to_job(self, vac):
        """Map a single vacancy GraphQL object to the save_job_from_api expected dict.

        The mapping is conservative: fields that don't exist are skipped and reasonable
        defaults are used. The external_id will be the vacancy id prefixed with 'ajira:'.
        """
        try:
            vid = vac.get('id')
            scheme = vac.get('scheme') or {}
            title = scheme.get('codeNo') or f"Vacancy {vid}"
            company = (scheme.get('emp') or {}).get('name') or 'Ajira Portal'
            open_date = vac.get('openDate')
            close_date = vac.get('closeDate')

            # Convert dates if present to datetime where possible; leave as-is otherwise
            application_deadline = None
            if close_date:
                try:
                    application_deadline = datetime.fromisoformat(close_date)
                except Exception:
                    application_deadline = None

            job = {
                'title': title,
                'company_name': company,
                'location': 'Tanzania',
                'description': '',
                'requirements': '',
                'responsibilities': '',
                'job_type': 'full_time',
                'experience_level': 'mid',
                'application_deadline': application_deadline or (timezone.now() + timezone.timedelta(days=30)),
                'external_url': f"{self.base_url.rstrip('/')}/vacancy/{vid}",
                'external_id': f"ajira:{vid}",
                'source': 'ajira'
            }
            return job
        except Exception as e:
            logger.error(f"Error mapping vacancy {vac}: {e}")
            return None
