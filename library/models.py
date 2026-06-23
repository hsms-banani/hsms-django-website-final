# library/models.py
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import uuid
import hashlib
import unicodedata
import re
from django.contrib.auth.hashers import make_password
import logging
from utils.image_optimizer import optimize_image

logger = logging.getLogger(__name__)

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
    def with_publication_counts(self):
        return self.annotate(publication_count=models.Count('publications'))
    
    def by_language(self, language_code):
        return self.filter(publications__language=language_code).distinct()

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
    def with_publication_counts(self):
        return self.annotate(publication_count=models.Count('publications'))

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
    def with_publication_counts(self):
        return self.annotate(publication_count=models.Count('publications'))
    
    def by_language(self, language_code):
        return self.filter(publications__language=language_code).distinct()

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

class Publication(models.Model):
    """Abstract base class for all library publications (e.g., books, magazines)."""
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

    title = models.CharField(max_length=500, db_index=True)
    title_bangla = models.CharField(max_length=500, blank=True, help_text="Title in Bangla")
    subtitle = models.CharField(max_length=500, blank=True)
    subtitle_bangla = models.CharField(max_length=500, blank=True, help_text="Subtitle in Bangla")
    slug = models.SlugField(max_length=500, unique=True, blank=True, db_index=True)
    
    accession_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique accession number for this item (e.g., ACC-2024-001)"
    )
    
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name='%(class)s_publications', db_index=True)
    publication_year = models.PositiveIntegerField(
        db_index=True,
        validators=[MinValueValidator(1000), MaxValueValidator(2025)]
    )
    
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
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='%(class)s_publications', db_index=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en', db_index=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True)
    description_bangla = models.TextField(blank=True, help_text="Description in Bangla")
    keywords = models.CharField(max_length=500, blank=True, db_index=True)
    keywords_bangla = models.CharField(max_length=500, blank=True, db_index=True)
    
    total_copies = models.PositiveIntegerField(default=1)
    copies_available = models.PositiveIntegerField(default=1, db_index=True)
    location_shelf = models.CharField(max_length=50, blank=True, help_text="Physical location (e.g., A-1-3)")
    
    status = models.CharField(max_length=20, choices=AVAILABILITY_STATUS, default='available', db_index=True)
    acquisition_date = models.DateField(auto_now_add=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cover_image = models.ImageField(upload_to='library/covers/', blank=True, null=True)
    
    times_borrowed = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['accession_number']),
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
            while type(self).objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        if self.classification_number and self.cutter_number:
            self.call_number = f"{self.classification_number} {self.cutter_number}"
        
        if self.copies_available > self.total_copies:
            self.copies_available = self.total_copies
            
        if self.cover_image and not getattr(self, '_cover_optimized', False):
            optimized = optimize_image(self.cover_image, max_width=800, max_height=800)
            if optimized:
                self.cover_image = optimized
            self._cover_optimized = True
            
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        return self.copies_available > 0 and self.status == 'available'

    @property
    def is_multilingual(self):
        return bool(self.title_bangla or self.description_bangla)

    def __str__(self):
        title = self.title_bangla if self.title_bangla and not self.title else self.title
        return f"{title} - {self.accession_number}"


class Book(Publication):
    """Model for books in the library."""
    authors = models.ManyToManyField(Author, related_name='publications')
    isbn_10 = models.CharField(max_length=50, blank=True, db_index=True, help_text="10-digit ISBN (or variation)")
    isbn_13 = models.CharField(max_length=50, blank=True, db_index=True, help_text="13-digit ISBN (or variation)")
    edition = models.CharField(max_length=50, blank=True)
    volume = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Volume number (e.g., v1, v2, Vol. 1, Part 2)"
    )

    objects = BookManager()

    def get_absolute_url(self):
        return reverse('library:book_detail', kwargs={'slug': self.slug})

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


class Periodical(Publication):
    """Model for periodicals (magazines, journals) in the library."""
    issn = models.CharField(max_length=50, blank=True, db_index=True, help_text="8-digit ISSN (or variation)")
    issue_date = models.DateField(db_index=True)
    volume = models.CharField(max_length=20, blank=True, db_index=True)
    issue_number = models.CharField(max_length=20, blank=True, db_index=True)

    class Meta(Publication.Meta):
        verbose_name_plural = "Periodicals"
    
    def get_absolute_url(self):
        return reverse('library:periodical_detail', kwargs={'slug': self.slug})

    def __str__(self):
        title = self.title_bangla if self.title_bangla and not self.title else self.title
        return f"{title} (V:{self.volume}, I:{self.issue_number}) - {self.accession_number}"

class BorrowRecord(models.Model):
    """Track book borrowing with email reminder support"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
    ]
    
    # Generic Foreign Key to Publication
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    publication = GenericForeignKey('content_type', 'object_id')
    
    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_records', related_query_name='borrowed_record')
    
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
    

    def clean(self):
        """Validate borrow record before saving"""
        super().clean()
        
        # Validate due date is in future
        if self.due_date and self.due_date < timezone.now().date():
            raise ValidationError({
                'due_date': 'Due date cannot be in the past.'
            })
        
        # Validate borrow date is not in future
        if self.borrow_date and self.borrow_date > timezone.now():
            raise ValidationError({
                'borrow_date': 'Borrow date cannot be in the future.'
            })
        
        # Validate return date is after borrow date
        if self.return_date and self.borrow_date:
            if self.return_date.date() < self.borrow_date.date():
                raise ValidationError({
                    'return_date': 'Return date cannot be before borrow date.'
                })
        
        # Validate fine amount is non-negative
        if self.fine_amount and self.fine_amount < 0:
            raise ValidationError({
                'fine_amount': 'Fine amount cannot be negative.'
            })
        
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation:
            self.full_clean()
        
        # Auto-update overdue status and calculate fines
        if self.status == 'active' and timezone.now().date() > self.due_date:
            self.status = 'overdue'
            days_overdue = (timezone.now().date() - self.due_date).days
            setting = LibrarySetting.objects.first()
            fine_per_day = setting.overdue_fine_per_day if setting else 10.00
            self.fine_amount = days_overdue * fine_per_day
        
        super().save(*args, **kwargs)

    @property
    def is_renewable(self):
        """Check if book can be renewed"""
        if self.status != 'active':
            return False
        
        if self.is_overdue:
            return False
        
        setting = LibrarySetting.objects.first()
        max_renewals = setting.max_renewals if setting else 2
        
        if self.renewal_count >= max_renewals:
            return False
        
        # Check if there are holds/reservations for this book
        # (Future feature: implement hold system)
        
        return True

    
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
        logger.info(f"Returning publication: {self.publication.title}, copies available before: {self.publication.copies_available}, status before: {self.publication.status}")
        self.return_date = timezone.now()
        self.status = 'returned'
        self.publication.copies_available += 1
        if self.publication.copies_available > 0:
            self.publication.status = 'available'
        self.publication.save()
        self.save(skip_validation=True)
        logger.info(f"Returned publication: {self.publication.title}, copies available after: {self.publication.copies_available}, status after: {self.publication.status}")

    def undo_return(self):
        """Undo a return, reverting the publication to its previous state."""
        logger.info(f"Undoing return for publication: {self.publication.title}, copies available before: {self.publication.copies_available}, status before: {self.publication.status}")
        if self.status != 'returned':
            raise ValueError("This publication has not been returned yet.")

        if self.publication.copies_available < 1:
            raise ValueError("Cannot undo return, no copies available to be made unavailable.")

        self.return_date = None
        if self.due_date < timezone.now().date():
            self.status = 'overdue'
        else:
            self.status = 'active'
        
        self.publication.copies_available -= 1
        if self.publication.copies_available == 0:
            self.publication.status = 'checked_out'
        self.publication.save()
        self.save(skip_validation=True)
        logger.info(f"Undone return for publication: {self.publication.title}, copies available after: {self.publication.copies_available}, status after: {self.publication.status}")
    
    def __str__(self):
        publication_title = self.publication.title if self.publication else "Unknown Publication"
        borrower_name = self.borrower.get_full_name() if self.borrower else "Unknown Borrower"
        return f"{borrower_name} - {publication_title} (Due: {self.due_date})"

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

    # Additional settings
    send_reminder_3_days = models.BooleanField(
        default=True,
        help_text="Send reminder 3 days before due date"
    )
    
    send_reminder_1_day = models.BooleanField(
        default=True,
        help_text="Send reminder 1 day before due date"
    )
    
    send_overdue_notices = models.BooleanField(
        default=True,
        help_text="Send overdue notices automatically"
    )
    
    overdue_notice_frequency_days = models.PositiveIntegerField(
        default=7,
        help_text="How often to send overdue notices (in days)"
    )
    
    allow_self_return = models.BooleanField(
        default=False,
        help_text="Allow users to mark books as returned (requires staff approval)"
    )
    
    require_librarian_approval = models.BooleanField(
        default=False,
        help_text="Require librarian approval for borrowing"
    )
    
    def clean(self):
        """Validate library settings"""
        super().clean()
        
        if self.overdue_fine_per_day < 0:
            raise ValidationError({
                'overdue_fine_per_day': 'Fine amount cannot be negative.'
            })
        
        if self.loan_period < 1:
            raise ValidationError({
                'loan_period': 'Loan period must be at least 1 day.'
            })
        
        if self.max_renewals < 0:
            raise ValidationError({
                'max_renewals': 'Maximum renewals cannot be negative.'
            })
        
        if self.max_books_per_user < 1:
            raise ValidationError({
                'max_books_per_user': 'Must allow at least 1 book per user.'
            })
    
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


class LibraryPasswordSettings(models.Model):
    """Singleton model to store the default password for new users"""
    default_password = models.CharField(
        max_length=255, 
        help_text="Default password for new library users. This will be hashed automatically."
    )

    def save(self, *args, **kwargs):
        """Enforce a single instance and hash the password"""
        if not self.pk and LibraryPasswordSettings.objects.exists():
            raise ValidationError("There can be only one LibraryPasswordSettings instance.")
        
        # Hash the password before saving
        self.default_password = make_password(self.default_password)
        return super(LibraryPasswordSettings, self).save(*args, **kwargs)

    def clean(self):
        """Validate library password settings"""
        super().clean()
        
        if not self.default_password:
            raise ValidationError({
                'default_password': 'Default password cannot be empty.'
            })

    class Meta:
        verbose_name = "Library Password Setting"
        verbose_name_plural = "Library Password Settings"

    def __str__(self):
        return "Library Password Settings"