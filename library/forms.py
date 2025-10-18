# library/forms.py

from django import forms
from .models import Book, Category, Author, Publisher
from django_select2.forms import Select2MultipleWidget

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'title_bangla': forms.TextInput(attrs={'class': 'form-input'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-input'}),
            'subtitle_bangla': forms.TextInput(attrs={'class': 'form-input'}),
            'accession_number': forms.TextInput(attrs={'class': 'form-input'}),
            'volume': forms.TextInput(attrs={'class': 'form-input'}),
            'authors': Select2MultipleWidget(attrs={'class': 'form-select'}),
            'publisher': forms.Select(attrs={'class': 'form-select'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-input'}),
            'isbn_10': forms.TextInput(attrs={'class': 'form-input'}),
            'isbn_13': forms.TextInput(attrs={'class': 'form-input'}),
            'classification_number': forms.TextInput(attrs={'class': 'form-input'}),
            'cutter_number': forms.TextInput(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'pages': forms.NumberInput(attrs={'class': 'form-input'}),
            'edition': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'description_bangla': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'keywords': forms.TextInput(attrs={'class': 'form-input'}),
            'keywords_bangla': forms.TextInput(attrs={'class': 'form-input'}),
            'total_copies': forms.NumberInput(attrs={'class': 'form-input'}),
            'copies_available': forms.NumberInput(attrs={'class': 'form-input'}),
            'location_shelf': forms.TextInput(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-input'}),
        }


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