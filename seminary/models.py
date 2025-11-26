# seminary/models.py
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from tinymce.models import HTMLField

class SiteSettings(models.Model):
    site_name = models.CharField(max_length=200, default="Holy Spirit Major Seminary")
    site_motto = models.CharField(max_length=200, default="Dedicated for Service")
    site_logo = models.ImageField(upload_to='site/', blank=True, null=True)
    hsit_logo = models.ImageField(upload_to='site/', blank=True, null=True)
    address = HTMLField(help_text="Use rich text formatting for address")  # Rich text
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    google_analytics_id = models.CharField(max_length=50, blank=True, help_text="Google Analytics Tracking ID")
    meta_description = models.CharField(max_length=160, blank=True, help_text="Default meta description for SEO")
    meta_keywords = models.CharField(max_length=255, blank=True, help_text="Default meta keywords for SEO")
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return self.site_name


class Banner(models.Model):
    PAGE_CHOICES = [
        ('home', 'Home'),
        ('publications', 'Publications'),
        ('news', 'News'),
        ('events', 'Events'),
        ('gallery', 'Gallery'),
        ('contact', 'Contact'),
        ('about', 'About'),
        ('spiritual-food', 'Spiritual Food'),
        ('seminary-history', 'Seminary History'),
        ('formation-program', 'Formation Program'),
        ('rules-regulations', 'Rules & Regulations'),
        ('committees', 'Committees'),
        ('philosophy-department', 'Philosophy Department'),
        ('church-history', 'Church History'),
        ('local-church-history', 'Local Church History'),
        ('bangladesh-history', 'Bangladesh History'),
        ('history-heritage', 'History & Heritage'),
        ('prayer-services', 'Prayer Services'),
        ('homilies', 'Homilies'),
        ('hsit-about', 'HSIT About'),
        ('theology-department', 'Theology Department'),
        ('default-banner', 'Default Banner'),
    ]
    page = models.CharField(max_length=50, choices=PAGE_CHOICES, unique=True, help_text="Select the page where this banner will be displayed.")
    image = models.ImageField(upload_to='banners/', help_text="Upload a banner image. Recommended size: 1920x400 pixels.")
    title = models.CharField(max_length=200, blank=True, help_text="Optional: A title to display on the banner.")
    subtitle = models.CharField(max_length=300, blank=True, help_text="Optional: A subtitle to display on the banner.")
    is_active = models.BooleanField(default=True, help_text="Enable or disable this banner.")

    def __str__(self):
        return self.get_page_display()



class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = HTMLField(blank=True, help_text="Department description with rich formatting")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Faculty(models.Model):
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=100)
    departments = models.ManyToManyField(Department, related_name='faculty')
    bio = HTMLField(blank=True, null=True, help_text="Faculty biography with rich text formatting")  # Optional Rich text
    photo = models.ImageField(upload_to='faculty/', blank=True, null=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    qualifications = HTMLField(blank=True, help_text="Academic qualifications with formatting")  # Rich text
    specialization = models.CharField(max_length=200, blank=True, help_text="Area of specialization")
    office_hours = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Order of display")
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(blank=True, null=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Faculty"
    
    def __str__(self):
        return f"{self.name} - {self.title}"

    def get_absolute_url(self):
        return reverse('faculty_detail', kwargs={'pk': self.pk})
    

class SeminaryAdministration(models.Model):
    """Seminary Administration members model"""
    name = models.CharField(max_length=200, help_text="Full name of the administrator")
    photo = models.ImageField(
        upload_to='administration/', 
        blank=True, 
        null=True,
        help_text="Administrator's photo (recommended: 400x400px)"
    )
    designation = models.CharField(
        max_length=200, 
        help_text="Official title/position (e.g., Rector, Vice Rector, Bursar)"
    )
    bio = HTMLField(
        blank=True, 
        null=True,
        help_text="Brief biography or background information"
    )
    email = models.EmailField(blank=True, help_text="Official email address")
    phone = models.CharField(max_length=20, blank=True, help_text="Contact phone number")
    office_location = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Office location or room number"
    )
    office_hours = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Available office hours"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    is_active = models.BooleanField(default=True, help_text="Show on website")
    start_date = models.DateField(
        blank=True, 
        null=True, 
        help_text="When this person started in this role"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Seminary Administrator"
        verbose_name_plural = "Seminary Administration"
    
    def __str__(self):
        return f"{self.name} - {self.designation}"
    
    def get_absolute_url(self):
        return reverse('administration_detail', kwargs={'pk': self.pk})
    
    @property
    def display_name(self):
        """Get formatted name for display"""
        return self.name
    
    @property
    def has_contact_info(self):
        """Check if administrator has contact information"""
        return bool(self.email or self.phone or self.office_location)
    

class Page(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = HTMLField(help_text="Page content with rich text formatting")  # Rich text
    excerpt = HTMLField(blank=True, help_text="Short excerpt or summary")  # Rich text
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    featured_image = models.ImageField(upload_to='pages/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    show_in_menu = models.BooleanField(default=False, help_text="Show this page in navigation menu")
    parent_page = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, help_text="Parent page for hierarchical structure")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('page_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('page_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class News(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = HTMLField(help_text="News content with rich text formatting")  # Rich text
    excerpt = models.CharField(max_length=300, blank=True,)
    featured_image = models.ImageField(upload_to='news/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    publish_date = models.DateTimeField(blank=True, null=True, help_text="Schedule publication date")
    meta_description = models.CharField(max_length=160, blank=True)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "News"
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('news_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class Event(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = HTMLField(help_text="Event description with rich text formatting")  # Rich text
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    organizer = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    registration_required = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(blank=True, null=True)
    max_participants = models.PositiveIntegerField(blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, choices=[
        ('conference', 'Conference'),
        ('seminar', 'Seminar'),
        ('workshop', 'Workshop'),
        ('celebration', 'Celebration'),
        ('retreat', 'Retreat'),
        ('other', 'Other')
    ])
    featured_image = models.ImageField(upload_to='events/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['start_date']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'slug': self.slug})
    
    @property
    def is_upcoming(self):
        from django.utils import timezone
        return self.start_date > timezone.now()
    
    @property
    def is_ongoing(self):
        from django.utils import timezone
        now = timezone.now()
        return self.start_date <= now <= (self.end_date or self.start_date)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class Publication(models.Model):
    PUBLICATION_TYPES = [
        ('ankur', 'Ankur - Newsletter'),
        ('diptto_sakhyo', 'Diptto Sakhyo - Major Seminary Journal'),
        ('prodipon', 'Prodipon - Theological Journal'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    publication_type = models.CharField(max_length=20, choices=PUBLICATION_TYPES)
    content = HTMLField(help_text="Publication content with rich text formatting")  # Rich text
    abstract = HTMLField(blank=True, help_text="Publication abstract with formatting")  # Rich text
    author = models.CharField(max_length=200)
    co_authors = models.CharField(max_length=500, blank=True, help_text="Co-authors if any")
    publication_date = models.DateField()
    volume = models.CharField(max_length=20, blank=True)
    issue = models.CharField(max_length=20, blank=True)
    page_numbers = models.CharField(max_length=20, blank=True, help_text="e.g., 15-25")
    pdf_file = models.FileField(
        upload_to='publications/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    cover_image = models.ImageField(upload_to='publications/covers/', blank=True, null=True)
    keywords = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords")
    is_published = models.BooleanField(default=True)
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-publication_date']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('publication_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class Gallery(models.Model):
    GALLERY_TYPES = [
        ('photo', 'Photo Gallery'),
        ('video', 'Video Gallery'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    gallery_type = models.CharField(max_length=10, choices=GALLERY_TYPES, default='photo')
    cover_image = models.ImageField(upload_to='gallery/covers/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Galleries"
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('gallery_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class GalleryItem(models.Model):
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='gallery/', blank=True, null=True)
    video_url = models.URLField(blank=True, help_text="YouTube, Vimeo, or other video URL")
    
    # UPDATED: Removed file size validation, will be handled in settings and admin
    video_file = models.FileField(
        upload_to='gallery/videos/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'wmv', 'mkv', 'webm'])],
        help_text="Maximum file size: 200MB. Supported formats: MP4, AVI, MOV, WMV, MKV, WEBM"
    )
    
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-id']
        indexes = [
            models.Index(fields=['gallery', 'order']),
        ]
    
    def __str__(self):
        return f"{self.gallery.title} - {self.title or 'Item'}"



class Slider(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to='slider/')
    mobile_image = models.ImageField(upload_to='slider/mobile/', blank=True, null=True, help_text="Optimized image for mobile devices")
    link_url = models.URLField(blank=True)
    link_text = models.CharField(max_length=50, blank=True)
    button_style = models.CharField(max_length=20, choices=[
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('outline', 'Outline')
    ], default='primary')
    text_position = models.CharField(max_length=20, choices=[
        ('center', 'Center'),
        ('left', 'Left'),
        ('right', 'Right')
    ], default='center')
    overlay_opacity = models.DecimalField(max_digits=3, decimal_places=2, default=0.4, help_text="Background overlay opacity (0.0 to 1.0)")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(blank=True, null=True, help_text="Schedule slider start date")
    end_date = models.DateTimeField(blank=True, null=True, help_text="Schedule slider end date")
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title

class CommitteeMember(models.Model):
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name


class CommitteeType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon_class = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Committee(models.Model):
    name = models.CharField(max_length=200)
    committee_type = models.ForeignKey(CommitteeType, on_delete=models.SET_NULL, null=True, related_name='committees')
    description = HTMLField(help_text="Committee description with rich text formatting")  # Rich text
    responsibilities = HTMLField(blank=True, help_text="Committee responsibilities and duties")  # Rich text
    advisor = models.ForeignKey(
        Faculty, on_delete=models.SET_NULL, null=True, related_name='advised_committees'
    )
    members = models.ManyToManyField(CommitteeMember, related_name='committees', blank=True)
    is_active = models.BooleanField(default=True)
    established_date = models.DateField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=200)
    content = HTMLField(help_text="Announcement content with rich text formatting")  # Rich text
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    target_audience = models.CharField(max_length=100, choices=[
        ('all', 'All'),
        ('students', 'Students'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('visitors', 'Visitors'),
    ], default='all')
    is_active = models.BooleanField(default=True)
    show_on_homepage = models.BooleanField(default=False)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_current(self):
        from django.utils import timezone
        now = timezone.now()
        return self.start_date <= now <= self.end_date and self.is_active


class LeadershipMessage(models.Model):
    """Base model for leadership messages"""
    MESSAGE_TYPES = (
        ('rector', 'Rector Welcome'),
        ('director', 'Director Message'),
        ('spiritual_director', 'Spiritual Director Message'),
    )
    
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, unique=True)
    title = models.CharField(max_length=200)
    leader_name = models.CharField(max_length=100)
    leader_title = models.CharField(max_length=100)
    leader_photo = models.ImageField(upload_to='leadership/', blank=True, null=True, help_text="Leader's photo")
    message_content = HTMLField(help_text="Main message content with rich text formatting")
    quote = models.TextField(blank=True, help_text="Inspirational quote or highlight")
    
    # SEO fields
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    
    # Additional fields
    background_image = models.ImageField(upload_to='leadership/backgrounds/', blank=True, null=True, help_text="Background image for the page")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Leadership Message"
        verbose_name_plural = "Leadership Messages"
        ordering = ['message_type']
    
    def __str__(self):
        return f"{self.get_message_type_display()} - {self.leader_name}"
    
    def get_absolute_url(self):
        if self.message_type == 'rector':
            return reverse('rector_welcome')
        elif self.message_type == 'director':
            return reverse('director_message')
        elif self.message_type == 'spiritual_director':
            return reverse('spiritual_directors_desk')
        return '#'
    
    def save(self, *args, **kwargs):
        # Auto-set titles based on message type
        if self.message_type == 'rector' and not self.title:
            self.title = "Welcome from the Rector"
        elif self.message_type == 'spiritual_director' and not self.title:
            self.title = "Spiritual Director's Message"
        super().save(*args, **kwargs)

class CalendarEvent(models.Model):
    title = models.CharField(max_length=200)
    description = HTMLField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    is_all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)
    event_type = models.CharField(max_length=50, blank=True, choices=[
        ('academic', 'Academic'),
        ('holiday', 'Holiday'),
        ('meeting', 'Meeting'),
        ('other', 'Other')
    ])

    class Meta:
        ordering = ['start_date', 'start_time']

    def __str__(self):
        return self.title