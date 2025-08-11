import logging
from django.conf import settings
# APScheduler has been removed
from django.core.management.base import BaseCommand
from jobs.api_integration import fetch_all_jobs

logger = logging.getLogger(__name__)

def fetch_jobs_manually():
    """
    Manual function to fetch jobs - can be called from a management command
    or view as needed. APScheduler has been removed.
    """
    try:
        logger.info("Manually fetching jobs...")
        fetch_all_jobs()
        logger.info("Job fetch completed successfully")
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
