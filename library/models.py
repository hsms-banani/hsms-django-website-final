# library/models.py - Enhanced with Borrowing System, Accession Number, and Volume

from django.db import models, connection
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid
import hashlib
import unicodedata
import re

class LibraryUser(User):
    """Proxy model for library users to have separate admin interface"""
    class Meta:
        proxy = True
        verbose_name = 'Library User'
        verbose_name_plural = 'Library Users'

class BulkUserImportLog(models.Model):
    """Track bulk user imports"""
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bulk_imports')
    import_date = models.DateTimeField(auto_now_add=True)
    csv_file = models.FileField(upload_to='library/bulk_imports/', blank=True, null=True)
    total_records = models.PositiveIntegerField(default=0)
    successful_imports = models.PositiveIntegerField(default=0)
    failed_imports = models.PositiveIntegerField(default=0)
    error_log = models.TextField(blank=True, help_text="Errors encountered during import")
    success_log = models.TextField(blank=True, help_text="Successfully created users")
    
    class Meta:
        ordering = ['-import_date']
        verbose_name = 'Bulk User Import Log'
        verbose_name_plural = 'Bulk User Import Logs'
    
    def __str__(self):
        return f"Import on {self.import_date.strftime('%Y-%m-%d %H:%M')} by {self.imported_by}"


def create_unicode_safe_slug(text, max_length=50):
    """Create URL-safe slug that works with Bangla and other Unicode text"""
    if not text:
        return ""
    
    text = unicodedata.normalize('NFC', text)
    slug = slugify(text)
    if slug and len(slug) > 3:
        return slug[:max_length]
    
    english_words = re.findall(r'[A-Za-z]+', text)
    if english_words:
        base = slugify(' '.join(english_words[:2]))
    else:
        base = 'item'
    
    hash_obj = hashlib.md5(text.encode('utf-8'))
    hash_suffix = hash_obj.hexdigest()[:8]
    
    return f"{base}-{hash_suffix}"[:max_length]

class CategoryManager(models.Manager):
    def with_book_counts(self):
        return self.annotate(book_count=models.Count('books'))
    
    def by_language(self, language_code):
        return self.filter(books__language=language_code).distinct()

class Category(models.Model):
    """Book categories/subjects with Unicode support"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    name_bangla = models.CharField(max_length=100, blank=True, help_text="Category name in Bangla")
    slug = models.SlugField(max_length=100, unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    description_bangla = models.TextField(blank=True, help_text="Description in Bangla")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = CategoryManager()
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = create_unicode_safe_slug(self.name)
        super().save(*args, **kwargs)
    
    def get_display_name(self, language='en'):
        if language == 'bn' and self.name_bangla:
            return self.name_bangla
        return self.name
    
    def __str__(self):
        return self.name

class PublisherManager(models.Manager):
    def with_book_counts(self):
        return self.annotate(book_count=models.Count('books'))

class Publisher(models.Model):
    """Publishers with Unicode support"""
    name = models.CharField(max_length=200, unique=True, db_index=True)
    name_bangla = models.CharField(max_length=200, blank=True, help_text="Publisher name in Bangla")
    slug = models.SlugField(max_length=200, unique=True, blank=True, db_index=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    established_year = models.PositiveIntegerField(
        blank=True, 
        null=True,
        db_index=True,
        validators=[MinValueValidator(1000), MaxValueValidator(2025)]
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = PublisherManager()
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = create_unicode_safe_slug(self.name)
        super().save(*args, **kwargs)
    
    def get_display_name(self, language='en'):
        if language == 'bn' and self.name_bangla:
            return self.name_bangla
        return self.name
    
    def __str__(self):
        return self.name

class AuthorManager(models.Manager):
    def with_book_counts(self):
        return self.annotate(book_count=models.Count('books'))
    
    def by_language(self, language_code):
        return self.filter(books__language=language_code).distinct()

class Author(models.Model):
    """Authors with Unicode support"""
    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)
    first_name_bangla = models.CharField(max_length=100, blank=True, help_text="First name in Bangla")
    last_name_bangla = models.CharField(max_length=100, blank=True, help_text="Last name in Bangla")
    slug = models.SlugField(max_length=200, unique=True, blank=True, db_index=True)
    bio = models.TextField(blank=True)
    bio_bangla = models.TextField(blank=True, help_text="Biography in Bangla")
    birth_year = models.PositiveIntegerField(
        blank=True, null=True, db_index=True,
        validators=[MinValueValidator(1000), MaxValueValidator(2025)]
    )
    death_year = models.PositiveIntegerField(
        blank=True, null=True, db_index=True,
        validators=[MinValueValidator(1000), MaxValueValidator(2025)]
    )
    nationality = models.CharField(max_length=100, blank=True, db_index=True)
    primary_language = models.CharField(
        max_length=10, 
        choices=[('en', 'English'), ('bn', 'Bangla'), ('mixed', 'Mixed')],
        default='en',
        help_text="Primary language of the author's works"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = AuthorManager()
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['slug']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            full_name = f"{self.first_name} {self.last_name}"
            self.slug = create_unicode_safe_slug(full_name)
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def full_name_bangla(self):
        if self.first_name_bangla or self.last_name_bangla:
            return f"{self.first_name_bangla} {self.last_name_bangla}".strip()
        return ""
    
    def get_display_name(self, language='en'):
        if language == 'bn' and self.full_name_bangla:
            return self.full_name_bangla
        return self.full_name
    
    def __str__(self):
        return self.full_name

class BookManager(models.Manager):
    def available(self):
        return self.filter(status='available', copies_available__gt=0)
    
    def popular(self):
        return self.filter(times_borrowed__gte=5).order_by('-times_borrowed')
    
    def recent(self):
        return self.order_by('-created_at')
    
    def by_language(self, language_code):
        return self.filter(language=language_code)
    
    def with_full_details(self):
        return self.select_related('publisher', 'category').prefetch_related('authors')

class Book(models.Model):
    """Main Book model - Enhanced with Accession Number and Volume"""
    LANGUAGE_CHOICES = [
        ('en', 'English'), ('bn', 'বাংলা (Bangla)'), ('hi', 'Hindi'),
        ('ur', 'Urdu'), ('es', 'Spanish'), ('fr', 'French'),
        ('de', 'German'), ('it', 'Italian'), ('pt', 'Portuguese'),
        ('la', 'Latin'), ('gr', 'Greek'), ('he', 'Hebrew'),
        ('ar', 'Arabic'), ('mixed', 'Mixed Languages'), ('other', 'Other'),
    ]
    
    AVAILABILITY_STATUS = [
        ('available', 'Available'),
        ('checked_out', 'Checked Out'),
        ('reserved', 'Reserved'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('repair', 'Under Repair'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=500, db_index=True)
    title_bangla = models.CharField(max_length=500, blank=True, help_text="Title in Bangla")
    subtitle = models.CharField(max_length=500, blank=True)
    subtitle_bangla = models.CharField(max_length=500, blank=True, help_text="Subtitle in Bangla")
    slug = models.SlugField(max_length=500, unique=True, blank=True, db_index=True)
    
    # NEW: Accession Number and Volume
    accession_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique accession number for this book copy (e.g., ACC-2024-001)"
    )
    volume = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Volume number (e.g., v1, v2, Vol. 1, Part 2)"
    )
    
    authors = models.ManyToManyField(Author, related_name='books')
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name='books', db_index=True)
    publication_year = models.PositiveIntegerField(
        db_index=True,
        validators=[MinValueValidator(1000), MaxValueValidator(2025)]
    )
    
    # ISBN and Classification
    isbn_10 = models.CharField(max_length=10, blank=True, db_index=True, help_text="10-digit ISBN")
    isbn_13 = models.CharField(max_length=13, blank=True, db_index=True, help_text="13-digit ISBN")
    classification_number = models.CharField(
        max_length=50, db_index=True,
        help_text="Dewey Decimal Classification (e.g., 236.5)"
    )
    cutter_number = models.CharField(
        max_length=50, db_index=True,
        help_text="Cutter number (e.g., L43n)"
    )
    call_number = models.CharField(
        max_length=100, blank=True, db_index=True,
        help_text="Auto-generated from classification + cutter number"
    )
    
    # Content Details
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='books', db_index=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en', db_index=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    edition = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    description_bangla = models.TextField(blank=True, help_text="Description in Bangla")
    keywords = models.CharField(max_length=500, blank=True, db_index=True)
    keywords_bangla = models.CharField(max_length=500, blank=True, db_index=True)
    
    # Physical Details
    total_copies = models.PositiveIntegerField(default=1)
    copies_available = models.PositiveIntegerField(default=1, db_index=True)
    location_shelf = models.CharField(max_length=50, blank=True, help_text="Physical location (e.g., A-1-3)")
    
    # Status and Metadata
    status = models.CharField(max_length=20, choices=AVAILABILITY_STATUS, default='available', db_index=True)
    acquisition_date = models.DateField(auto_now_add=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cover_image = models.ImageField(upload_to='library/covers/', blank=True, null=True)
    
    # Tracking
    times_borrowed = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    # PostgreSQL Full Text Search
    search_vector = SearchVectorField(null=True, blank=True)
    
    objects = BookManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['accession_number']),
            models.Index(fields=['volume']),
            models.Index(fields=['call_number']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            title_for_slug = self.title_bangla if self.title_bangla else self.title
            self.slug = create_unicode_safe_slug(title_for_slug)
            counter = 1
            original_slug = self.slug
            while Book.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        if self.classification_number and self.cutter_number:
            self.call_number = f"{self.classification_number} {self.cutter_number}"
        
        if self.copies_available > self.total_copies:
            self.copies_available = self.total_copies
            
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('library:book_detail', kwargs={'slug': self.slug})

    @property
    def is_available(self):
        return self.copies_available > 0 and self.status == 'available'

    @property
    def is_multilingual(self):
        """Check if the book has content in both English and Bangla."""
        return bool(self.title_bangla or self.description_bangla)

    @property
    def full_call_number(self):
        """Return complete call number with volume if applicable"""
        base = self.call_number
        if self.volume:
            return f"{base} {self.volume}"
        return base
    
    def __str__(self):
        title = self.title_bangla if self.title_bangla and not self.title else self.title
        volume_str = f" ({self.volume})" if self.volume else ""
        return f"{title}{volume_str} - {self.accession_number}"

class BorrowRecord(models.Model):
    """Track book borrowing with email reminder support"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
    ]
    
    # Foreign Keys
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrow_records')
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_books')
    
    # Borrowing Details
    borrow_date = models.DateTimeField(default=timezone.now, db_index=True)
    due_date = models.DateField(db_index=True)
    return_date = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Status and Fines
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine_paid = models.BooleanField(default=False, db_index=True)
    
    # Renewal Tracking
    renewal_count = models.PositiveIntegerField(default=0)
    renewal_date = models.DateTimeField(null=True, blank=True, help_text="Date of the last renewal")
    
    # Email Reminders
    first_reminder_sent = models.DateTimeField(null=True, blank=True)
    second_reminder_sent = models.DateTimeField(null=True, blank=True)
    overdue_reminder_sent = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-borrow_date']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['borrower', 'status']),
            models.Index(fields=['-borrow_date']),
            models.Index(fields=['due_date']),
        ]
        verbose_name = "Borrow Record"
        verbose_name_plural = "Borrow Records"
    
    def save(self, *args, **kwargs):
        # Calculate fine for overdue books
        if self.status == 'active' and timezone.now().date() > self.due_date:
            self.status = 'overdue'
            days_overdue = (timezone.now().date() - self.due_date).days
            # Use the configurable fine from LibrarySetting
            setting = LibrarySetting.objects.first()
            fine_per_day = setting.overdue_fine_per_day if setting else 10.00
            self.fine_amount = days_overdue * fine_per_day
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        return self.status == 'active' and timezone.now().date() > self.due_date
    
    @property
    def days_until_due(self):
        if self.status != 'active':
            return None
        return (self.due_date - timezone.now().date()).days
    
    @property
    def can_renew(self):
        setting = LibrarySetting.objects.first()
        max_renewals = setting.max_renewals if setting else 2
        return self.status == 'active' and self.renewal_count < max_renewals and not self.is_overdue
    
    def renew(self, days=None):
        """Renew the book for additional days"""
        if not self.can_renew:
            raise ValueError("Cannot renew this book")
        
        setting = LibrarySetting.objects.first()
        renewal_days = days if days is not None else (setting.renewal_period if setting else 14)
        self.due_date = timezone.now().date() + timedelta(days=renewal_days)
        self.renewal_count += 1
        self.renewal_date = timezone.now()
        self.save()
        return True
    
    def return_book(self):
        """Mark book as returned and update availability"""
        self.return_date = timezone.now()
        self.status = 'returned'
        self.book.copies_available += 1
        self.book.save()
        self.save()
    
    def __str__(self):
        return f"{self.borrower.get_full_name()} - {self.book.title} (Due: {self.due_date})"

class BookSearch(models.Model):
    """Track popular searches"""
    query = models.CharField(max_length=200, db_index=True, unique=True)
    language_detected = models.CharField(
        max_length=10, 
        choices=[('en', 'English'), ('bn', 'Bangla'), ('mixed', 'Mixed')],
        default='en'
    )
    search_count = models.PositiveIntegerField(default=1, db_index=True)
    last_searched = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-search_count', '-last_searched']
        indexes = [
            models.Index(fields=['-search_count', '-last_searched']),
        ]
    
    def __str__(self):
        return f"{self.query} ({self.search_count} searches)"

class LibrarySetting(models.Model):
    """Singleton model to store library-wide settings"""
    overdue_fine_per_day = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=10.00,
        help_text="Fine for each day a book is overdue (in BDT)"
    )
    loan_period = models.PositiveIntegerField(
        default=14, 
        help_text="Initial loan period in days"
    )
    renewal_period = models.PositiveIntegerField(
        default=14, 
        help_text="Number of days for each renewal"
    )
    max_renewals = models.PositiveIntegerField(
        default=2, 
        help_text="Maximum number of times a book can be renewed"
    )
    max_books_per_user = models.PositiveIntegerField(
        default=5, 
        help_text="Maximum number of books a user can borrow at a time"
    )
    
    class Meta:
        verbose_name = "Library Setting"
        verbose_name_plural = "Library Settings"

    def save(self, *args, **kwargs):
        """Enforce a single instance of library settings"""
        if not self.pk and LibrarySetting.objects.exists():
            # Intercept creation of a new instance if one already exists
            raise ValidationError("There can be only one LibrarySetting instance.")
        return super(LibrarySetting, self).save(*args, **kwargs)

    def __str__(self):
        return "Library Settings"