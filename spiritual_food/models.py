# spiritual_food/models.py
from django.db import models
from django.utils.text import slugify
from django.core.validators import URLValidator
from tinymce.models import HTMLField
from utils.image_optimizer import optimize_image

class Announcement(models.Model):
    """Model for scrolling announcements"""
    CONTENT_TYPE_CHOICES = [
        ('text', 'Text'),
        ('pdf', 'PDF'),
        ('image', 'Image'),
    ]
    
    title = models.CharField(max_length=200)
    short_description = models.TextField(max_length=300, help_text="Brief description for scrolling display")
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES, default='text')
    
    # Content fields
    text_content = HTMLField(blank=True, null=True, help_text="Full text content")
    pdf_file = models.FileField(upload_to='announcements/pdfs/', blank=True, null=True)
    image_file = models.ImageField(upload_to='announcements/images/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher priority shows first")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Leave blank for no expiration")
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.image_file and not getattr(self, '_image_optimized', False):
            optimized = optimize_image(self.image_file, max_width=1920, max_height=1080)
            if optimized:
                self.image_file = optimized
            self._image_optimized = True
        super().save(*args, **kwargs)

class PrayerService(models.Model):
    """Model for prayer services schedule"""
    DAY_CHOICES = [
        ('daily', 'Daily'),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
        ('special', 'Special Occasion'),
    ]
    
    SERVICE_TYPE_CHOICES = [
        ('mass', 'Holy Mass'),
        ('adoration', 'Eucharistic Adoration'),
        ('rosary', 'Holy Rosary'),
        ('vespers', 'Evening Prayer (Vespers)'),
        ('lauds', 'Morning Prayer (Lauds)'),
        ('compline', 'Night Prayer (Compline)'),
        ('novena', 'Novena'),
        ('other', 'Other'),
    ]
    
    service_name = models.CharField(max_length=200)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES)
    day = models.CharField(max_length=20, choices=DAY_CHOICES)
    time = models.TimeField()
    location = models.CharField(max_length=200, default="Chapel")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'time']
        verbose_name = "Prayer Service"
        verbose_name_plural = "Prayer Services"
    
    def __str__(self):
        return f"{self.service_name} - {self.get_day_display()} {self.time.strftime('%I:%M %p')}"


class HomilyCategory(models.Model):
    """Categories for organizing homilies"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Homily Category"
        verbose_name_plural = "Homily Categories"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Homily(models.Model):
    """Model for homilies in text and video format"""
    LITURGICAL_SEASON_CHOICES = [
        ('advent', 'Advent'),
        ('christmas', 'Christmas'),
        ('ordinary', 'Ordinary Time'),
        ('lent', 'Lent'),
        ('easter', 'Easter'),
        ('special', 'Special Feasts'),
    ]
    
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    preacher = models.CharField(max_length=200, help_text="Name of the preacher")
    date = models.DateField()
    
    # Liturgical information
    liturgical_season = models.CharField(max_length=20, choices=LITURGICAL_SEASON_CHOICES, blank=True)
    sunday_reading = models.CharField(max_length=100, blank=True, help_text="e.g., 3rd Sunday of Advent")
    scripture_reference = models.CharField(max_length=300, blank=True, help_text="e.g., Matthew 5:1-12")
    
    # Content
    summary = models.TextField(max_length=500, help_text="Brief summary for preview")
    text_content = HTMLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True, validators=[URLValidator()], 
                                   help_text="Full YouTube video URL")
    
    # Organization
    category = models.ForeignKey(HomilyCategory, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.CharField(max_length=300, blank=True, help_text="Comma-separated tags")
    
    # Media
    thumbnail = models.ImageField(upload_to='homilies/thumbnails/', blank=True, null=True)
    
    # Metadata
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Homily"
        verbose_name_plural = "Homilies"
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['liturgical_season']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.thumbnail and not getattr(self, '_thumbnail_optimized', False):
            optimized = optimize_image(self.thumbnail, max_width=800, max_height=800)
            if optimized:
                self.thumbnail = optimized
            self._thumbnail_optimized = True
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} - {self.date.strftime('%B %d, %Y')}"
    
    def get_youtube_embed_id(self):
        """Extract YouTube video ID from URL"""
        if not self.youtube_url:
            return None
        
        # Handle various YouTube URL formats
        if 'youtu.be/' in self.youtube_url:
            return self.youtube_url.split('youtu.be/')[-1].split('?')[0]
        elif 'youtube.com/watch?v=' in self.youtube_url:
            return self.youtube_url.split('watch?v=')[-1].split('&')[0]
        elif 'youtube.com/embed/' in self.youtube_url:
            return self.youtube_url.split('embed/')[-1].split('?')[0]
        return None


class PrayerRequest(models.Model):
    """Model for prayer/mass intentions"""
    REQUEST_TYPE_CHOICES = [
        ('prayer', 'Prayer Intention'),
        ('mass', 'Mass Intention'),
        ('thanksgiving', 'Thanksgiving'),
        ('healing', 'Healing'),
        ('guidance', 'Guidance'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('prayed', 'Prayed For'),
    ]
    
    # Requester Information
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Request Details
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    intention = models.TextField(help_text="Please describe your prayer intention")
    preferred_date = models.DateField(blank=True, null=True, help_text="For Mass intentions")
    
    # Privacy
    make_public = models.BooleanField(default=False, help_text="Allow this intention to be shared publicly")
    
    # Donation
    wants_to_donate = models.BooleanField(default=False)
    donation_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    donation_reference = models.CharField(max_length=100, blank=True, help_text="Transaction reference number")
    
    # Administrative
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Prayer Request"
        verbose_name_plural = "Prayer Requests"
    
    def __str__(self):
        return f"{self.name} - {self.get_request_type_display()} ({self.created_at.strftime('%Y-%m-%d')})"


class DonationInfo(models.Model):
    """Model for donation information"""
    PAYMENT_METHOD_CHOICES = [
        ('bkash', 'bKash'),
        ('bank', 'Bank Transfer'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
    ]
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, unique=True)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=200, blank=True, help_text="For bank transfers")
    branch_name = models.CharField(max_length=200, blank=True)
    routing_number = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=50, blank=True)
    
    instructions = models.TextField(blank=True, help_text="Additional instructions for donors")
    qr_code = models.ImageField(upload_to='donation/qr_codes/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'payment_method']
        verbose_name = "Donation Information"
        verbose_name_plural = "Donation Information"
    
    def __str__(self):
        return f"{self.get_payment_method_display()} - {self.account_number}"

    def save(self, *args, **kwargs):
        if self.qr_code and not getattr(self, '_qr_optimized', False):
            optimized = optimize_image(self.qr_code, max_width=800, max_height=800)
            if optimized:
                self.qr_code = optimized
            self._qr_optimized = True
        super().save(*args, **kwargs)

class Saint(models.Model):
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    feast_day = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name

class LiturgicalCalendar(models.Model):
    """Model for Liturgical Calendar events"""
    SEASON_CHOICES = [
        ('advent', 'Advent'),
        ('christmas', 'Christmas'),
        ('ordinary', 'Ordinary Time'),
        ('lent', 'Lent'),
        ('easter', 'Easter'),
    ]
    
    RANK_CHOICES = [
        ('solemnity', 'Solemnity'),
        ('sunday', 'Sunday'),
        ('feast', 'Feast'),
        ('memorial', 'Memorial'),
        ('optional-memorial', 'Optional Memorial'),
        ('weekday', 'Weekday'),
    ]

    COLOR_CHOICES = [
        ('green', 'Green'),
        ('white', 'White'),
        ('red', 'Red'),
        ('violet', 'Violet'),
        ('rose', 'Rose'),
    ]

    CYCLE_CHOICES = [
        ('A', 'Year A'),
        ('B', 'Year B'),
        ('C', 'Year C'),
        ('I', 'Year I'),
        ('II', 'Year II'),
    ]

    name = models.CharField(max_length=200)
    date = models.DateField(unique=True)
    season = models.CharField(max_length=20, choices=SEASON_CHOICES, blank=True)
    rank = models.CharField(max_length=20, choices=RANK_CHOICES, default='weekday')
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='green')
    secondary_color = models.CharField(max_length=10, choices=COLOR_CHOICES, blank=True, null=True, help_text="Optional secondary color (e.g. White when primary color is Green)")
    
    # Primary Readings
    first_reading = models.CharField(max_length=100, blank=True)
    responsorial_psalm = models.CharField(max_length=100, blank=True)
    second_reading = models.CharField(max_length=100, blank=True)
    gospel = models.CharField(max_length=100, blank=True)
    
    # Alternative Reading Set ("Or / অথবা")
    alt_reading_title = models.CharField(max_length=200, blank=True, help_text="Title for alternative readings, e.g. 'Or Common of Saints' / 'অথবা বাণীবিতান'")
    alt_first_reading = models.CharField(max_length=100, blank=True, help_text="Alternative 1st Reading")
    alt_responsorial_psalm = models.CharField(max_length=100, blank=True, help_text="Alternative Psalm")
    alt_second_reading = models.CharField(max_length=100, blank=True, help_text="Alternative 2nd Reading")
    alt_gospel = models.CharField(max_length=100, blank=True, help_text="Alternative Gospel")
    
    # Local Commemorations & Necrology
    commemorations = models.TextField(blank=True, help_text="Local diocese/seminary commemorations or necrology (+ deceased priests/religious)")
    
    cycle = models.CharField(max_length=2, choices=CYCLE_CHOICES, blank=True)
    saints = models.ManyToManyField(Saint, blank=True)
    is_holy_day_of_obligation = models.BooleanField(default=False, help_text="Is this a holy day of obligation?")
    
    class Meta:
        ordering = ['date']
        verbose_name = "Liturgical Calendar Event"
        verbose_name_plural = "Liturgical Calendar Events"

    def __str__(self):
        return f"{self.name} - {self.date.strftime('%B %d, %Y')}"

        

class PrayerRequestSettings(models.Model):
    """Singleton model to configure prayer request handling"""
    send_email_notifications = models.BooleanField(
        default=True,
        help_text="Enable to send prayer requests to a designated email address."
    )
    notification_email = models.EmailField(
        blank=True,
        help_text="The email address to receive prayer request notifications."
    )
    keep_a_copy = models.BooleanField(
        default=True,
        help_text="Save a copy of each prayer request in the admin panel."
    )

    class Meta:
        verbose_name = "Prayer Request Settings"
        verbose_name_plural = "Prayer Request Settings"

    def __str__(self):
        return "Prayer Request Settings"

    def save(self, *args, **kwargs):
        # Ensure there is only one instance of this model
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        # Convenience method to get the singleton instance
        obj, created = cls.objects.get_or_create(pk=1)
        return obj