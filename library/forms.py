# library/forms.py

from django import forms
from .models import Book, Category, Author, Publisher

class BookSearchForm(forms.Form):
    SORT_CHOICES = [
        ('-created_at', 'Newest First'),
        ('created_at', 'Oldest First'),
        ('title', 'Title A-Z'),
        ('-title', 'Title Z-A'),
        ('-publication_year', 'Publication Year (Newest)'),
        ('publication_year', 'Publication Year (Oldest)'),
        ('-times_borrowed', 'Most Popular'),
        ('times_borrowed', 'Least Popular'),
    ]
    
    AVAILABILITY_CHOICES = [
        ('', 'All Books'),
        ('available', 'Available Only'),
        ('unavailable', 'Not Available'),
    ]
    
    q = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search books, authors, ISBN, call number...',
            'autocomplete': 'off'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    author = forms.ModelChoiceField(
        queryset=Author.objects.all(),
        required=False,
        empty_label='All Authors',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    publisher = forms.ModelChoiceField(
        queryset=Publisher.objects.all(),
        required=False,
        empty_label='All Publishers',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    language = forms.ChoiceField(
        choices=[('', 'All Languages')] + Book.LANGUAGE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    year_from = forms.IntegerField(
        required=False,
        min_value=1000,
        max_value=2025,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'From Year'
        })
    )
    
    year_to = forms.IntegerField(
        required=False,
        min_value=1000,
        max_value=2025,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'To Year'
        })
    )
    
    availability = forms.ChoiceField(
        choices=AVAILABILITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class QuickSearchForm(forms.Form):
    q = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Quick search...',
            'hx-get': '/library/api/quick-search/',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#quick-search-results',
            'autocomplete': 'off'
        })
    )