# library/cron.py
"""
Cron job functions for automated library tasks
"""

from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def send_daily_reminders():
    """Send daily email reminders for borrowed books"""
    try:
        logger.info("Starting daily email reminder job...")
        call_command('send_borrow_reminders')
        logger.info("Daily email reminder job completed successfully")
    except Exception as e:
        logger.error(f"Error in daily email reminder job: {str(e)}")

def update_overdue_books():
    """Update overdue book statuses and calculate fines"""
    try:
        logger.info("Starting overdue book update job...")
        from django.utils import timezone
        from .models import BorrowRecord
        
        today = timezone.now().date()
        
        # Find active books past due date
        overdue_records = BorrowRecord.objects.filter(
            status='active',
            due_date__lt=today
        )
        
        updated_count = 0
        for record in overdue_records:
            days_overdue = (today - record.due_date).days
            record.status = 'overdue'
                            record.fine_amount = days_overdue * 10.00            record.save(update_fields=['status', 'fine_amount'])
            updated_count += 1
        
        logger.info(f"Updated {updated_count} overdue records")
        
    except Exception as e:
        logger.error(f"Error in overdue book update job: {str(e)}")