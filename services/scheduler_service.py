import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

logger = logging.getLogger(__name__)

scheduler = None

def init_scheduler(app):
    """Initialize the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        return scheduler
    
    try:
        scheduler = BackgroundScheduler()
        
        # Schedule ingestion for 7:00 AM and 7:00 PM CET
        scheduler.add_job(
            func=run_scheduled_ingestion,
            trigger=CronTrigger(hour=7, minute=0, timezone='Europe/Madrid'),
            id='morning_ingestion',
            name='Morning Gmail Ingestion',
            replace_existing=True
        )
        
        scheduler.add_job(
            func=run_scheduled_ingestion,
            trigger=CronTrigger(hour=19, minute=0, timezone='Europe/Madrid'),
            id='evening_ingestion',
            name='Evening Gmail Ingestion',
            replace_existing=True
        )
        
        scheduler.start()
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
        
        logger.info("Scheduler initialized with ingestion jobs at 07:00 and 19:00 CET")
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {str(e)}")
        return None

def run_scheduled_ingestion():
    """Run the scheduled ingestion job"""
    try:
        logger.info("Starting scheduled Gmail ingestion")
        
        from services.gmail_service import GmailService
        gmail_service = GmailService()
        
        processed_count = gmail_service.run_ingestion()
        
        logger.info(f"Scheduled ingestion completed. Processed {processed_count} properties")
        
    except Exception as e:
        logger.error(f"Scheduled ingestion failed: {str(e)}")

def get_scheduler_status():
    """Get current scheduler status"""
    global scheduler
    
    if scheduler is None:
        return {"status": "not_initialized"}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs": jobs
    }
