# library/management/commands/send_borrow_reminders.py
"""
Management command to send email reminders for borrowed books
Run this daily via cron job:
0 9 * * * cd /path/to/project && python manage.py send_borrow_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from library.models import BorrowRecord
from library.email_service import LibraryEmailService

class Command(BaseCommand):
    help = 'Send email reminders for borrowed books'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()
        
        # Statistics
        first_reminders = 0
        second_reminders = 0
        overdue_notices = 0
        errors = 0
        
        self.stdout.write(self.style.SUCCESS(f'\n📧 Starting email reminder process for {today}...\n'))
        
        # ========================================
        # 1. First Reminder (3 days before due)
        # ========================================
        first_reminder_date = today + timedelta(days=3)
        first_reminder_records = BorrowRecord.objects.filter(
            status='active',
            due_date=first_reminder_date,
            first_reminder_sent__isnull=True
        ).select_related('book', 'borrower')
        
        self.stdout.write(f'📌 First Reminders (3 days before due): {first_reminder_records.count()} records\n')
        
        for record in first_reminder_records:
            try:
                if not dry_run:
                    success = LibraryEmailService.send_first_reminder(record)
                    if success:
                        first_reminders += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Sent first reminder to {record.borrower.email} for "{record.book.title}"'
                            )
                        )
                    else:
                        errors += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Failed to send first reminder to {record.borrower.email}'
                            )
                        )
                else:
                    first_reminders += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [DRY RUN] Would send first reminder to {record.borrower.email} for "{record.book.title}"'
                        )
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error sending first reminder: {str(e)}')
                )
        
        # ========================================
        # 2. Second Reminder (1 day before due)
        # ========================================
        second_reminder_date = today + timedelta(days=1)
        second_reminder_records = BorrowRecord.objects.filter(
            status='active',
            due_date=second_reminder_date,
            second_reminder_sent__isnull=True
        ).select_related('book', 'borrower')
        
        self.stdout.write(f'\n📌 Second Reminders (1 day before due): {second_reminder_records.count()} records\n')
        
        for record in second_reminder_records:
            try:
                if not dry_run:
                    success = LibraryEmailService.send_second_reminder(record)
                    if success:
                        second_reminders += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Sent second reminder to {record.borrower.email} for "{record.book.title}"'
                            )
                        )
                    else:
                        errors += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Failed to send second reminder to {record.borrower.email}'
                            )
                        )
                else:
                    second_reminders += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [DRY RUN] Would send second reminder to {record.borrower.email} for "{record.book.title}"'
                        )
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error sending second reminder: {str(e)}')
                )
        
        # ========================================
        # 3. Overdue Notices (past due date)
        # ========================================
        overdue_records = BorrowRecord.objects.filter(
            status='active',
            due_date__lt=today,
            overdue_reminder_sent__isnull=True
        ).select_related('book', 'borrower')
        
        # Also update status to overdue and calculate fines
        for record in overdue_records:
            if not dry_run:
                record.status = 'overdue'
                days_overdue = (today - record.due_date).days
                record.fine_amount = days_overdue * 5.00  # $5 per day
                record.save()
        
        self.stdout.write(f'\n📌 Overdue Notices (past due date): {overdue_records.count()} records\n')
        
        for record in overdue_records:
            try:
                if not dry_run:
                    success = LibraryEmailService.send_overdue_notice(record)
                    if success:
                        overdue_notices += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Sent overdue notice to {record.borrower.email} for "{record.book.title}" (Fine: ${record.fine_amount})'
                            )
                        )
                    else:
                        errors += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Failed to send overdue notice to {record.borrower.email}'
                            )
                        )
                else:
                    overdue_notices += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [DRY RUN] Would send overdue notice to {record.borrower.email} for "{record.book.title}"'
                        )
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error sending overdue notice: {str(e)}')
                )
        
        # ========================================
        # Summary
        # ========================================
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n📊 Email Reminder Summary:'))
        self.stdout.write(f'  First Reminders: {first_reminders}')
        self.stdout.write(f'  Second Reminders: {second_reminders}')
        self.stdout.write(f'  Overdue Notices: {overdue_notices}')
        self.stdout.write(f'  Total Sent: {first_reminders + second_reminders + overdue_notices}')
        self.stdout.write(f'  Errors: {errors}')
        self.stdout.write('='*60 + '\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a DRY RUN. No emails were sent.\n'))