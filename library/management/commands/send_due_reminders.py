# library/management/commands/send_due_reminders.py
"""
Automated command to send due date reminders
Run this daily via cron job or celery beat
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from library.models import BorrowRecord
from library.email_service import LibraryEmailService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send automated email reminders for due books'

    def handle(self, *args, **options):
        today = timezone.now().date()
        sent_count = 0
        error_count = 0
        
        # First reminder: 3 days before due
        first_reminder_date = today + timedelta(days=3)
        first_reminders = BorrowRecord.objects.filter(
            status='active',
            due_date=first_reminder_date,
            first_reminder_sent__isnull=True
        )
        
        self.stdout.write(f'Found {first_reminders.count()} books due in 3 days')
        
        for record in first_reminders:
            try:
                LibraryEmailService.send_first_reminder(record)
                sent_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f'Failed to send first reminder for record {record.id}: {str(e)}')
        
        # Second reminder: 1 day before due
        second_reminder_date = today + timedelta(days=1)
        second_reminders = BorrowRecord.objects.filter(
            status='active',
            due_date=second_reminder_date,
            second_reminder_sent__isnull=True
        )
        
        self.stdout.write(f'Found {second_reminders.count()} books due tomorrow')
        
        for record in second_reminders:
            try:
                LibraryEmailService.send_second_reminder(record)
                sent_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f'Failed to send second reminder for record {record.id}: {str(e)}')
        
        # Overdue notices
        overdue_records = BorrowRecord.objects.filter(
            status='active',
            due_date__lt=today
        )
        
        self.stdout.write(f'Found {overdue_records.count()} overdue books')
        
        try:
                record.status = 'overdue'
                days_overdue = (today - record.due_date).days
                
                # Get fine rate from settings
                from library.models import LibrarySetting
                setting = LibrarySetting.objects.first()
                fine_per_day = setting.overdue_fine_per_day if setting else 10.00
                
                record.fine_amount = days_overdue * fine_per_day
                record.save()
                
                # Send overdue notice (send weekly to avoid spam)
                if not record.overdue_reminder_sent or \
                   (timezone.now() - record.overdue_reminder_sent).days >= 7:
                    LibraryEmailService.send_overdue_notice(record)
                    sent_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f'Failed to process overdue record {record.id}: {str(e)}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Reminder processing complete. Sent: {sent_count}, Errors: {error_count}'
            )
        )