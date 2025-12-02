# seminary/forms.py
from django import forms
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Your Full Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Your Email Address'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Your Phone Number (Optional)'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Your Message',
            'rows': 6
        })
    )
    
    def send_email(self):
        """Send contact form email"""
        subject = f"Contact Form: {self.cleaned_data['subject']}"
        message = f"""
        Name: {self.cleaned_data['name']}
        Email: {self.cleaned_data['email']}
        Phone: {self.cleaned_data.get('phone', 'Not provided')}
        
        Message:
        {self.cleaned_data['message']}
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['hsmsmajorseminary@gmail.com'],  # Seminary email
                fail_silently=False,
            )
            logger.info(f"Contact form email sent successfully from {self.cleaned_data['email']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send contact form email: {str(e)}")
            print(f"Email Error: {str(e)}")  # Also print to console for debugging
            return False
