# spiritual_food/forms.py
from django import forms
from django.core.validators import EmailValidator
from .models import PrayerRequest


class PrayerRequestForm(forms.ModelForm):
    """Form for submitting prayer requests"""
    
    class Meta:
        model = PrayerRequest
        fields = [
            'name', 'email', 'phone', 'request_type', 
            'intention', 'preferred_date', 'make_public',
            'wants_to_donate', 'donation_amount', 'donation_reference'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Your Full Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'your.email@example.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': '+880 1XX XXX XXXX (Optional)',
            }),
            'request_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'intention': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Please share your prayer intention...',
                'rows': 5,
            }),
            'preferred_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'date',
            }),
            'make_public': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500',
            }),
            'wants_to_donate': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500',
                'x-model': 'wantsToDonate',
            }),
            'donation_amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Amount (optional)',
                'step': '0.01',
                'x-show': 'wantsToDonate',
            }),
            'donation_reference': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Transaction Reference Number',
                'x-show': 'wantsToDonate',
            }),
        }
        
        labels = {
            'name': 'Full Name *',
            'email': 'Email Address *',
            'phone': 'Phone Number',
            'request_type': 'Type of Request *',
            'intention': 'Prayer Intention *',
            'preferred_date': 'Preferred Date (for Mass Intentions)',
            'make_public': 'I allow this intention to be shared publicly',
            'wants_to_donate': 'I would like to make a donation',
            'donation_amount': 'Donation Amount (BDT)',
            'donation_reference': 'Transaction Reference',
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            validator = EmailValidator()
            validator(email)
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        wants_to_donate = cleaned_data.get('wants_to_donate')
        donation_reference = cleaned_data.get('donation_reference')
        
        # If user wants to donate but hasn't provided reference, show warning
        if wants_to_donate and donation_reference:
            # Optionally validate reference format here
            pass
        
        return cleaned_data