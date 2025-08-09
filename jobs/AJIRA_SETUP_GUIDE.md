# Ajira Portal Integration - Quick Setup Guide

Follow these steps to set up the Ajira Portal job scraper in your project:

## 1. Install Required Packages

Make sure you have the required packages installed:

```bash
pip install -r requirements.txt
```

## 2. Configure Ajira Portal API in Admin Panel

1. Go to the Django admin panel
2. Navigate to "Jobs" > "API Configurations"
3. Click "Add API Configuration"
4. Fill in the following details:
   - API Name: Select "Ajira Portal" from the dropdown
   - API Key: Enter any non-empty value (e.g., "ajira-key")
   - API Secret: Leave blank
   - Additional Parameters: Leave as empty "{}"
   - Is Active: Check this box
5. Click "Save"

## 3. Run the Scraper Manually

To test the integration, you can run the scraper manually:

```bash
python manage.py fetch_ajira_jobs
```

The jobs will be imported and will show up in the "Jobs" section of the admin panel.

## 4. Automatic Scraping

The jobs will be automatically refreshed every 6 hours as part of the scheduled task system.

## 5. Troubleshooting

If you encounter any issues:

1. Check the Django logs for error messages
2. Verify that you can access the Ajira Portal website in your browser
3. Check the API Request Logs in the admin panel for detailed error information

## 6. Customization

If you need to modify how the scraper works:

- The scraper implementation is in `jobs/api_integration.py` in the `AjiraJobsClient` class
- The scheduler configuration is in `jobs/scheduler.py`
- Management command is in `jobs/management/commands/fetch_ajira_jobs.py`

## Important Notes

- The scraper uses requests with SSL verification disabled due to potential issues with the Ajira Portal's SSL certificates
- Expired jobs are automatically marked as inactive based on their application deadline
- Duplicate jobs are detected using the external URL, so each job is only imported once
