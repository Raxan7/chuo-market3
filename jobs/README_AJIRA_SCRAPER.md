# Ajira Portal Job Scraper

This integration allows the system to automatically scrape job listings from the Ajira Portal (https://portal.ajira.go.tz/) and import them into the database.

## Features

- Scrapes all job categories from Ajira Portal
- Extracts detailed job information including title, description, requirements, and application deadlines
- Prevents duplicate job listings
- Automatically marks expired jobs as inactive
- Scheduled automatic updates every 6 hours
- Manual update option via management command

## Setup Instructions

1. Create an API Configuration for Ajira Portal in the admin panel:
   - Name: `ajira`
   - API Key: Any non-empty value (not actually used but required by the model)
   - API Secret: Leave blank
   - Check "Is Active"

2. Jobs will be automatically fetched as part of the regular job fetching schedule.

3. To manually fetch jobs from Ajira Portal, run:
   ```
   python manage.py fetch_ajira_jobs
   ```

## How It Works

- The scraper navigates to all job category pages on the Ajira Portal
- For each job listing, it extracts the summary information and follows the "More Details" link
- On the detail page, it extracts the full job description, requirements, and employer information
- The system then processes this information and saves it to the database:
  - If a job with the same external ID already exists, it updates the existing record
  - If the job is new, it creates a new record
  - If a job has passed its application deadline, it's marked as inactive

## Troubleshooting

- SSL certificate verification is disabled for the Ajira Portal requests as the site might have certificate issues
- If you encounter rate limiting or blocking, try adjusting the request headers in the `AjiraJobsClient` class
- Check the logs for detailed error information if the scraper fails to run properly
