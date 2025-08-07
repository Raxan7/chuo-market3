# Django Job Portal App

A comprehensive job portal application for the Chuo Market platform.

## Features

- Job listing and searching functionality
- Integration with external job APIs (LinkedIn, Indeed, Adzuna, BrighterMonday)
- Scheduled job fetching from external sources
- Job application management
- Company profiles and verification
- User job preferences and automated matching
- Email notifications for new matching jobs
- REST API for mobile app integration

## Setup

1. Install required dependencies:
   ```
   pip install django-apscheduler
   ```

2. Configure API credentials:
   - Copy `.env.example` to `.env`
   - Add your API credentials for LinkedIn, Indeed, Adzuna, and BrighterMonday

3. Run migrations:
   ```
   python manage.py migrate jobs
   ```

4. Start the scheduler (or ensure it's enabled in settings.py):
   ```
   python manage.py runserver
   ```

## Templates

The app includes the following templates:
- `base.html`: Base template with sidebar for job search and filtering
- `job_list.html`: Displays job listings with search and filtering
- `job_detail.html`: Shows detailed information about a specific job
- `job_apply.html`: Application form for submitting job applications
- `job_post.html`: Form for employers to post new job listings
- `dashboard.html`: Main user dashboard for job seekers and employers
- `saved_jobs.html`: Displays jobs saved by the user
- `my_applications.html`: Lists and tracks user's job applications
- `application_detail.html`: Shows detailed information about an application
- `job_preferences.html`: Form for setting job preferences and alerts

## Static Files

- CSS styles in `static/jobs/css/jobs.css`
- JavaScript functionality in `static/jobs/js/jobs.js`

## API Integration

The app integrates with the following job portals:
- LinkedIn
- Indeed
- Adzuna
- BrighterMonday Tanzania

Jobs are fetched automatically using django-apscheduler.

## Management Commands

Fetch jobs manually:
```
python manage.py fetch_jobs
```

## Models

- `Company`: Represents employers posting jobs
- `Job`: Job listings (both internal and from external APIs)
- `JobApplication`: Track user applications to jobs
- `JobSearch`: Store user search preferences
- `SavedJob`: Jobs saved by users for later viewing
- `JobAlert`: User preferences for job notifications
- `JobCategory`: Categorization of jobs
- `JobSkill`: Skills associated with jobs

## Views

- Job listing and search views
- Job detail view
- Application submission and management
- Company profile creation and management
- User dashboard for applications
- REST API endpoints

## URLs

The app is mounted at `/jobs/` in the main project URLs.

## Future Enhancements

- Resume parsing and automatic skill matching
- Interview scheduling
- Enhanced analytics for job postings
- Chat functionality between employers and applicants
