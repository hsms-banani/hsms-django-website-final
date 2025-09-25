# library/models.py - Performance Optimized Version

from django.db import models, connection
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
import uuid

class CategoryManager(models.Manager):
    def with_book_counts(self):
        return self.annotate(book_count=models.Count('books'))

class Category(models.Model):
    """Book categories/subjects"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
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
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class PublisherManager(models.Manager):
    def with_book_counts(self):
        return self.annotate(book_count=models.Count('books'))

class Publisher(models.Model):
    """Publishers"""
    name = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True, db_index=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    established_year = models.PositiveIntegerField(
        blank=True, 
        null=True,
        db_index=True,
        validators=[
            MinValueValidator(1000),
            MaxValueValidator(2025)
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = PublisherManager()
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['established_year']),
            models.Index(fields=['-created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class AuthorManager(models.Manager):
    def with_book_counts(self):
        return self.annotate(book_count=models.Count('books'))

class Author(models.Model):
    """Authors"""
    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True, db_index=True)
    bio = models.TextField(blank=True)
    birth_year = models.PositiveIntegerField(
        blank=True, 
        null=True,
        db_index=True,
        validators=[
            MinValueValidator(1000),
            MaxValueValidator(2025)
        ]
    )
    death_year = models.PositiveIntegerField(
        blank=True, 
        null=True,
        db_index=True,
        validators=[
            MinValueValidator(1000),
            MaxValueValidator(2025)
        ]
    )
    nationality = models.CharField(max_length=100, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = AuthorManager()
    
    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['slug']),
            models.Index(fields=['nationality']),
            models.Index(fields=['birth_year']),
            models.Index(fields=['-created_at']),
            # Composite index for common queries
            models.Index(fields=['last_name', 'first_name', 'nationality']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            full_name = f"{self.first_name}-{self.last_name}"
            self.slug = slugify(full_name)
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return self.full_name

class BookManager(models.Manager):
    def available(self):
        return self.filter(status='available', copies_available__gt=0)
    
    def popular(self):
        return self.filter(times_borrowed__gte=5).order_by('-times_borrowed')
    
    def recent(self):
        return self.order_by('-created_at')
    
    def with_full_details(self):
        """Optimized queryset with all related data"""
        return self.select_related('publisher', 'category').prefetch_related('authors')

class Book(models.Model):
    """Main Book model - Performance Optimized"""
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('bn', 'Bangla'),
        ('hi', 'Hindi'),
        ('ur', 'Urdu'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('it', 'Italian'),
        ('pt', 'Portuguese'),
        ('la', 'Latin'),
        ('gr', 'Greek'),
        ('he', 'Hebrew'),
        ('ar', 'Arabic'),
        ('other', 'Other'),
    ]
    
    AVAILABILITY_STATUS = [
        ('available', 'Available'),
        ('checked_out', 'Checked Out'),
        ('reserved', 'Reserved'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('repair', 'Under Repair'),
    ]
    
    # Basic Information - with db_index for frequently searched fields
    title = models.CharField(max_length=500, db_index=True)
    subtitle = models.CharField(max_length=500, blank=True)
    slug = models.SlugField(max_length=500, unique=True, blank=True, db_index=True)
    authors = models.ManyToManyField(Author, related_name='books')
    publisher = models.ForeignKey(
        Publisher, 
        on_delete=models.CASCADE, 
        related_name='books',
        db_index=True
    )
    publication_year = models.PositiveIntegerField(
        db_index=True,
        validators=[
            MinValueValidator(1000),
            MaxValueValidator(2025)
        ]
    )
    
    # ISBN and Classification - heavily indexed for searches
    isbn_10 = models.CharField(max_length=10, blank=True, db_index=True, help_text="10-digit ISBN")
    isbn_13 = models.CharField(max_length=13, blank=True, db_index=True, help_text="13-digit ISBN")
    classification_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Dewey Decimal Classification (e.g., 236.5)"
    )
    cutter_number = models.CharField(
        max_length=50, 
        db_index=True,
        help_text="Cutter number (e.g., L43n)"
    )
    call_number = models.CharField(
        max_length=100, 
        blank=True,
        db_index=True,
        help_text="Auto-generated from classification + cutter number"
    )
    
    # Content Details
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='books',
        db_index=True
    )
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en', db_index=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    edition = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    keywords = models.CharField(
        max_length=500, 
        blank=True,
        db_index=True,  # For keyword searches
        help_text="Comma-separated keywords for better searchability"
    )
    
    # Physical Details
    total_copies = models.PositiveIntegerField(default=1)
    copies_available = models.PositiveIntegerField(default=1, db_index=True)
    location_shelf = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Physical location in library (e.g., A-1-3)"
    )
    
    # Status and Metadata - heavily indexed for filtering
    status = models.CharField(max_length=20, choices=AVAILABILITY_STATUS, default='available', db_index=True)
    acquisition_date = models.DateField(auto_now_add=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Cover image
    cover_image = models.ImageField(upload_to='library/covers/', blank=True, null=True)
    
    # Tracking - indexed for popularity sorting
    times_borrowed = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    # PostgreSQL Full Text Search Field (will be ignored on SQLite)
    search_vector = SearchVectorField(null=True, blank=True)
    
    objects = BookManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Single field indexes (most important)
            models.Index(fields=['title']),
            models.Index(fields=['slug']),
            models.Index(fields=['call_number']),
            models.Index(fields=['isbn_13']),
            models.Index(fields=['isbn_10']),
            models.Index(fields=['classification_number']),
            models.Index(fields=['status']),
            models.Index(fields=['copies_available']),
            models.Index(fields=['times_borrowed']),
            models.Index(fields=['publication_year']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['publisher']),
            models.Index(fields=['language']),
            
            # Composite indexes for common query patterns
            models.Index(fields=['status', 'copies_available']),  # For availability filtering
            models.Index(fields=['category', 'status']),         # For category + status filtering
            models.Index(fields=['publisher', 'status']),        # For publisher + status filtering
            models.Index(fields=['publication_year', 'status']), # For year + status filtering
            models.Index(fields=['-times_borrowed', 'status']),  # For popular available books
            models.Index(fields=['-created_at', 'status']),      # For recent available books
            models.Index(fields=['title', 'status']),            # For title searches with status
            
            # PostgreSQL specific - GIN index for full text search
        ]
        
        # Add PostgreSQL specific indexes if using PostgreSQL
        # This will be ignored on other databases
        indexes += [
            GinIndex(fields=['search_vector'], name='book_search_vector_gin_idx'),
        ] if connection.vendor == 'postgresql' else []
    
    def save(self, *args, **kwargs):
        # Auto-generate slug
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure uniqueness
            counter = 1
            original_slug = self.slug
            while Book.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Auto-generate call number
        if self.classification_number and self.cutter_number:
            self.call_number = f"{self.classification_number} {self.cutter_number}"
        
        # Ensure copies_available doesn't exceed total_copies
        if self.copies_available > self.total_copies:
            self.copies_available = self.total_copies
            
        super().save(*args, **kwargs)
        
        # Update search vector for PostgreSQL after save
        if hasattr(self, '_state') and self._state.db and 'postgresql' in self._state.db:
            self.update_search_vector()
    
    def update_search_vector(self):
        """Update PostgreSQL search vector"""
        from django.contrib.postgres.search import SearchVector
        from django.db import connection
        
        if 'postgresql' not in connection.vendor:
            return
            
        # Build search vector from multiple fields
        search_vector = (
            SearchVector('title', weight='A') +
            SearchVector('subtitle', weight='B') +
            SearchVector('keywords', weight='B') +
            SearchVector('description', weight='C')
        )
        
        # Update this specific book's search vector
        Book.objects.filter(pk=self.pk).update(search_vector=search_vector)
    
    def get_absolute_url(self):
        return reverse('library:book_detail', kwargs={'slug': self.slug})
    
    @property
    def is_available(self):
        return self.copies_available > 0 and self.status == 'available'
    
    @property
    def authors_list(self):
        """Cached property for author names"""
        if not hasattr(self, '_authors_list'):
            self._authors_list = ", ".join([author.full_name for author in self.authors.all()])
        return self._authors_list
    
    @property
    def primary_isbn(self):
        return self.isbn_13 if self.isbn_13 else self.isbn_10
    
    def __str__(self):
        return f"{self.title} - {self.authors_list}"

class BookSearch(models.Model):
    """Track popular searches for analytics - Optimized"""
    query = models.CharField(max_length=200, db_index=True, unique=True)
    search_count = models.PositiveIntegerField(default=1, db_index=True)
    last_searched = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-search_count', '-last_searched']
        indexes = [
            models.Index(fields=['-search_count', '-last_searched']),
            models.Index(fields=['query']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.query} ({self.search_count} searches)"