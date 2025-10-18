# library/email_service.py
"""
Professional Email Service for Library Borrowing System
Supports multiple email backends including SendGrid, Mailgun, and AWS SES
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint

logger = logging.getLogger(__name__)

class LibraryEmailService:
    """
    Centralized email service for library notifications
    """
    
    DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'library@hsms.edu')
    
    @staticmethod
    def _send_brevo_email(subject, html_content, recipient_email, recipient_name):
        """Helper function to send email using Brevo API"""
        configuration = sib_api_v3_sdk.Configuration()
        if not settings.EMAIL_HOST_PASSWORD:
            logger.error("Brevo API key is not set. Please set the EMAIL_HOST_PASSWORD environment variable.")
            return False
        configuration.api_key['api-key'] = settings.EMAIL_HOST_PASSWORD
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        
        sender = {"name": "HSMS Library", "email": LibraryEmailService.DEFAULT_FROM_EMAIL}
        to = [{"email": recipient_email, "name": recipient_name}]
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            sender=sender,
            subject=subject,
            html_content=html_content
        )
        
        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            pprint(api_response)
            return True
        except ApiException as e:
            logger.error(f"Exception when calling TransactionalEmailsApi->send_transac_email: {e}")
            return False

    @staticmethod
    def send_borrow_confirmation(borrow_record):
        """Send confirmation email when book is borrowed"""
        try:
            subject = f'Book Borrowed: {borrow_record.book.title}'
            
            context = {
                'borrower': borrow_record.borrower,
                'book': borrow_record.book,
                'borrow_record': borrow_record,
                'due_date': borrow_record.due_date,
                'library_name': 'HSMS Library',
            }
            
            html_message = render_to_string('library/emails/borrow_confirmation.html', context)
            
            if LibraryEmailService._send_brevo_email(subject, html_message, borrow_record.borrower.email, borrow_record.borrower.get_full_name()):
                logger.info(f"Borrow confirmation sent to {borrow_record.borrower.email}")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Failed to send borrow confirmation: {str(e)}")
            return False
    
    @staticmethod
    def send_first_reminder(borrow_record):
        """Send first reminder 3 days before due date"""
        try:
            subject = f'Reminder: Book Due in 3 Days - {borrow_record.book.title}'
            
            context = {
                'borrower': borrow_record.borrower,
                'book': borrow_record.book,
                'borrow_record': borrow_record,
                'due_date': borrow_record.due_date,
                'days_remaining': borrow_record.days_until_due,
                'can_renew': borrow_record.can_renew,
                'library_name': 'HSMS Library',
            }
            
            html_message = render_to_string('library/emails/first_reminder.html', context)
            
            if LibraryEmailService._send_brevo_email(subject, html_message, borrow_record.borrower.email, borrow_record.borrower.get_full_name()):
                borrow_record.first_reminder_sent = timezone.now()
                borrow_record.save(update_fields=['first_reminder_sent'])
                logger.info(f"First reminder sent to {borrow_record.borrower.email}")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Failed to send first reminder: {str(e)}")
            return False
    
    @staticmethod
    def send_second_reminder(borrow_record):
        """Send second reminder 1 day before due date"""
        try:
            subject = f'Urgent: Book Due Tomorrow - {borrow_record.book.title}'
            
            context = {
                'borrower': borrow_record.borrower,
                'book': borrow_record.book,
                'borrow_record': borrow_record,
                'due_date': borrow_record.due_date,
                'can_renew': borrow_record.can_renew,
                'library_name': 'HSMS Library',
            }
            
            html_message = render_to_string('library/emails/second_reminder.html', context)
            
            if LibraryEmailService._send_brevo_email(subject, html_message, borrow_record.borrower.email, borrow_record.borrower.get_full_name()):
                borrow_record.second_reminder_sent = timezone.now()
                borrow_record.save(update_fields=['second_reminder_sent'])
                logger.info(f"Second reminder sent to {borrow_record.borrower.email}")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Failed to send second reminder: {str(e)}")
            return False
    
    @staticmethod
    def send_overdue_notice(borrow_record):
        """Send overdue notice with fine information"""
        try:
            subject = f'Overdue Book Notice - {borrow_record.book.title}'
            
            context = {
                'borrower': borrow_record.borrower,
                'book': borrow_record.book,
                'borrow_record': borrow_record,
                'due_date': borrow_record.due_date,
                'fine_amount': borrow_record.fine_amount,
                'days_overdue': (timezone.now().date() - borrow_record.due_date).days,
                'library_name': 'HSMS Library',
            }
            
            html_message = render_to_string('library/emails/overdue_notice.html', context)
            
            if LibraryEmailService._send_brevo_email(subject, html_message, borrow_record.borrower.email, borrow_record.borrower.get_full_name()):
                borrow_record.overdue_reminder_sent = timezone.now()
                borrow_record.save(update_fields=['overdue_reminder_sent'])
                logger.info(f"Overdue notice sent to {borrow_record.borrower.email}")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Failed to send overdue notice: {str(e)}")
            return False
    
    @staticmethod
    def send_renewal_confirmation(borrow_record):
        """Send confirmation when book is renewed"""
        try:
            subject = f'Book Renewed: {borrow_record.book.title}'
            
            context = {
                'borrower': borrow_record.borrower,
                'book': borrow_record.book,
                'borrow_record': borrow_record,
                'new_due_date': borrow_record.due_date,
                'renewals_remaining': borrow_record.max_renewals - borrow_record.renewal_count,
                'library_name': 'HSMS Library',
            }
            
            html_message = render_to_string('library/emails/renewal_confirmation.html', context)
            
            if LibraryEmailService._send_brevo_email(subject, html_message, borrow_record.borrower.email, borrow_record.borrower.get_full_name()):
                logger.info(f"Renewal confirmation sent to {borrow_record.borrower.email}")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Failed to send renewal confirmation: {str(e)}")
            return False
    
    @staticmethod
    def send_return_confirmation(borrow_record):
        """Send confirmation when book is returned"""
        try:
            subject = f'Book Returned: {borrow_record.book.title}'
            
            context = {
                'borrower': borrow_record.borrower,
                'book': borrow_record.book,
                'borrow_record': borrow_record,
                'return_date': borrow_record.return_date,
                'fine_amount': borrow_record.fine_amount if borrow_record.fine_amount > 0 else None,
                'library_name': 'HSMS Library',
            }
            
            html_message = render_to_string('library/emails/return_confirmation.html', context)
            
            if LibraryEmailService._send_brevo_email(subject, html_message, borrow_record.borrower.email, borrow_record.borrower.get_full_name()):
                logger.info(f"Return confirmation sent to {borrow_record.borrower.email}")
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Failed to send return confirmation: {str(e)}")
            return False