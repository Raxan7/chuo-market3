import logging
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management.base import BaseCommand
from jobs.api_integration import fetch_all_jobs

logger = logging.getLogger(__name__)

def start_scheduler():
    """Start the background scheduler to fetch jobs periodically"""
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Schedule job to fetch from APIs every 6 hours
    scheduler.add_job(
        fetch_all_jobs,
        trigger=IntervalTrigger(hours=6),
        id="fetch_jobs",
        max_instances=1,
        replace_existing=True
    )
    
    # Start the scheduler
    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        
    return scheduler
