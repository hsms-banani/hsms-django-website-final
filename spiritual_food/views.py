# spiritual_food/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, F
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime

from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import (
    Announcement, PrayerService, Homily, 
    HomilyCategory, PrayerRequest, DonationInfo, PrayerRequestSettings, LiturgicalCalendar
)
from .forms import PrayerRequestForm

def send_prayer_request_email(prayer_request, recipient_email):
    """Sends prayer request details to the designated email"""
    subject = f"New Prayer Request from {prayer_request.name}"
    
    # Render the email content from a template
    html_message = render_to_string(
        'spiritual_food/email/prayer_request_notification.html', 
        {'prayer_request': prayer_request}
    )
    
    send_mail(
        subject,
        message='New prayer request received.',  # Plain text fallback
        from_email=None,  # Use default from_email
        recipient_list=[recipient_email],
        html_message=html_message,
        fail_silently=False,
    )



from seminary.models import Banner
def spiritual_food_home(request):
    """
    Home page displaying active announcements and featured content
    """
    try:
        banner = Banner.objects.get(page='spiritual-food', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    # Get active announcements that haven't expired
    now = timezone.now()
    announcements = Announcement.objects.filter(
        is_active=True
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).order_by('-priority', '-created_at')[:10]
    
    # Get featured homilies
    featured_homilies = Homily.objects.filter(
        is_published=True,
        is_featured=True
    ).order_by('-date')[:3]
    
    # Get today's prayer services
    today = datetime.now().strftime('%A').lower()
    daily_services = PrayerService.objects.filter(
        is_active=True,
        day='daily'
    ).order_by('time')
    
    today_services = PrayerService.objects.filter(
        is_active=True,
        day=today
    ).order_by('time')
    
    prayer_services = list(daily_services) + list(today_services)
    
    # Get recent homilies
    recent_homilies = Homily.objects.filter(
        is_published=True
    ).order_by('-date')[:6]
    
    context = {
        'announcements': announcements,
        'featured_homilies': featured_homilies,
        'prayer_services': prayer_services[:5],
        'recent_homilies': recent_homilies,
        'banner': banner,
    }
    
    return render(request, 'spiritual_food/home.html', context)


def announcement_detail(request, pk):
    """
    Display full announcement detail based on content type
    """
    announcement = get_object_or_404(Announcement, pk=pk, is_active=True)
    
    # Check if announcement has expired
    if announcement.expires_at and announcement.expires_at < timezone.now():
        messages.warning(request, "This announcement has expired.")
    
    context = {
        'announcement': announcement,
    }
    
    return render(request, 'spiritual_food/announcement_detail.html', context)


def prayer_services(request):
    """
    Display all prayer services organized by day
    """
    try:
        banner = Banner.objects.get(page='prayer-services', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    # Get filter parameters
    service_type = request.GET.get('type', None)
    day = request.GET.get('day', None)
    
    # Base queryset
    services = PrayerService.objects.filter(is_active=True).order_by('order', 'time')
    
    # Apply filters
    if service_type:
        services = services.filter(service_type=service_type)
    if day:
        services = services.filter(day=day)
    
    # Get all service types and days for filter options
    service_types = PrayerService.SERVICE_TYPE_CHOICES
    days = PrayerService.DAY_CHOICES
    
    # Organize services by day
    daily_services = services.filter(day='daily')
    special_services = services.filter(day='special')
    
    weekday_services = {}
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for weekday in weekdays:
        day_services = services.filter(day=weekday)
        if day_services.exists():
            weekday_services[weekday] = day_services
    
    context = {
        'services': services,
        'daily_services': daily_services,
        'weekday_services': weekday_services,
        'special_services': special_services,
        'service_types': service_types,
        'days': days,
        'selected_type': service_type,
        'selected_day': day,
        'banner': banner,
    }
    
    return render(request, 'spiritual_food/prayer_services.html', context)


class HomilyListView(ListView):
    """
    List view for homilies with filtering and searching
    """
    model = Homily
    template_name = 'spiritual_food/homily_list.html'
    context_object_name = 'homilies'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Homily.objects.filter(is_published=True).order_by('-date')
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(preacher__icontains=search_query) |
                Q(summary__icontains=search_query) |
                Q(scripture_reference__icontains=search_query) |
                Q(tags__icontains=search_query)
            )
        
        # Filter by category
        category_slug = self.request.GET.get('category', '')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter by liturgical season
        season = self.request.GET.get('season', '')
        if season:
            queryset = queryset.filter(liturgical_season=season)
        
        # Filter by year
        year = self.request.GET.get('year', '')
        if year:
            queryset = queryset.filter(date__year=year)
        
        # Filter by preacher
        preacher = self.request.GET.get('preacher', '')
        if preacher:
            queryset = queryset.filter(preacher__icontains=preacher)
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            banner = Banner.objects.get(page='homilies', is_active=True)
        except Banner.DoesNotExist:
            try:
                banner = Banner.objects.get(page='default-banner', is_active=True)
            except Banner.DoesNotExist:
                banner = None
        context['banner'] = banner
        
        # Add filter options
        context['categories'] = HomilyCategory.objects.all().order_by('order', 'name')
        context['seasons'] = Homily.LITURGICAL_SEASON_CHOICES
        
        # Get unique years from homilies
        years = Homily.objects.filter(
            is_published=True
        ).dates('date', 'year', order='DESC')
        context['years'] = [date.year for date in years]
        
        # Get unique preachers
        preachers = Homily.objects.filter(
            is_published=True
        ).values_list('preacher', flat=True).distinct().order_by('preacher')
        context['preachers'] = [p for p in preachers if p]
        
        # Pass current filters
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_season'] = self.request.GET.get('season', '')
        context['selected_year'] = self.request.GET.get('year', '')
        context['selected_preacher'] = self.request.GET.get('preacher', '')
        
        # Featured homilies
        context['featured_homilies'] = Homily.objects.filter(
            is_published=True,
            is_featured=True
        ).order_by('-date')[:3]
        
        return context


class HomilyDetailView(DetailView):
    """
    Detail view for individual homily
    """
    model = Homily
    template_name = 'spiritual_food/homily_detail.html'
    context_object_name = 'homily'
    
    def get_queryset(self):
        return Homily.objects.filter(is_published=True)
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        obj.views_count = F('views_count') + 1
        obj.save(update_fields=['views_count'])
        obj.refresh_from_db()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related homilies (same category or liturgical season)
        related_homilies = Homily.objects.filter(
            is_published=True
        ).exclude(
            id=self.object.id
        ).filter(
            Q(category=self.object.category) |
            Q(liturgical_season=self.object.liturgical_season)
        ).distinct().order_by('-date')[:4]
        
        context['related_homilies'] = related_homilies
        
        # Get YouTube embed ID
        context['youtube_embed_id'] = self.object.get_youtube_embed_id()
        
        return context


def homily_archive(request):
    """
    Archive view showing homilies organized by year and month
    """
    # Get all published homilies grouped by year and month
    homilies = Homily.objects.filter(is_published=True).order_by('-date')
    
    # Organize by year and month
    archive_data = {}
    for homily in homilies:
        year = homily.date.year
        month = homily.date.strftime('%B')
        
        if year not in archive_data:
            archive_data[year] = {}
        
        if month not in archive_data[year]:
            archive_data[year][month] = []
        
        archive_data[year][month].append(homily)
    
    # Sort years in descending order
    archive_data = dict(sorted(archive_data.items(), reverse=True))
    
    context = {
        'archive_data': archive_data,
    }
    
    return render(request, 'spiritual_food/homily_archive.html', context)


class PrayerRequestCreateView(CreateView):
    """
    Form view for creating prayer requests
    """
    model = PrayerRequest
    form_class = PrayerRequestForm
    template_name = 'spiritual_food/prayer_request.html'
    success_url = reverse_lazy('spiritual_food:prayer_request_success')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active donation information
        donation_methods = DonationInfo.objects.filter(is_active=True).order_by('order')
        context['donation_methods'] = donation_methods
        
        return context
    
    def form_valid(self, form):
        # Load prayer request settings
        settings = PrayerRequestSettings.load()
        
        # Decide whether to save the instance
        if settings.keep_a_copy:
            self.object = form.save()
        else:
            # Create an unsaved instance for email sending
            self.object = form.save(commit=False)

        # Send email notification if enabled
        if settings.send_email_notifications and settings.notification_email:
            try:
                send_prayer_request_email(self.object, settings.notification_email)
                messages.success(
                    self.request,
                    'Your prayer request has been submitted successfully. '
                    'We will keep you in our prayers.'
                )
            except Exception as e:
                messages.error(
                    self.request,
                    f'There was an error sending your request: {e}. '
                    'Please try again later.'
                )
                # If saving was skipped, we might need to reconsider
                if not settings.keep_a_copy:
                    return super().form_invalid(form)
        else:
            messages.success(
                self.request,
                'Your prayer request has been submitted successfully. '
                'We will keep you in our prayers.'
            )
        
        # If not saving, we still need to redirect to success URL
        if not settings.keep_a_copy:
            return redirect(self.get_success_url())
            
        return super().form_valid(form)

    
    def form_invalid(self, form):
        messages.error(
            self.request,
            'There was an error with your submission. '
            'Please check the form and try again.'
        )
        return super().form_invalid(form)


def prayer_request_success(request):
    """
    Success page after prayer request submission
    """
    return render(request, 'spiritual_food/prayer_request_success.html')


# Additional utility views

def public_prayer_intentions(request):
    """
    Display public prayer intentions (optional feature)
    """
    intentions = PrayerRequest.objects.filter(
        make_public=True,
        status='reviewed'
    ).order_by('-created_at')[:20]
    
    context = {
        'intentions': intentions,
    }
    
    return render(request, 'spiritual_food/public_intentions.html', context)


def search_all(request):
    """
    Global search across announcements, homilies, and prayer services
    """
    query = request.GET.get('q', '')
    
    results = {
        'announcements': [],
        'homilies': [],
        'prayer_services': [],
    }
    
    if query:
        # Search announcements
        results['announcements'] = Announcement.objects.filter(
            Q(title__icontains=query) |
            Q(short_description__icontains=query),
            is_active=True
        )[:5]
        
        # Search homilies
        results['homilies'] = Homily.objects.filter(
            Q(title__icontains=query) |
            Q(preacher__icontains=query) |
            Q(summary__icontains=query) |
            Q(scripture_reference__icontains=query),
            is_published=True
        )[:5]
        
        # Search prayer services
        results['prayer_services'] = PrayerService.objects.filter(
            Q(service_name__icontains=query) |
            Q(description__icontains=query),
            is_active=True
        )[:5]
    
    context = {
        'query': query,
        'results': results,
    }
    
    return render(request, 'spiritual_food/search_results.html', context)


from seminary.models import LeadershipMessage, Page
from collections import defaultdict

def liturgical_calendar(request):
    """
    Display the liturgical calendar, grouped by month, showing current and upcoming events.
    """
    today = timezone.now().date()
    events = LiturgicalCalendar.objects.filter(date__gte=today).order_by('date')
    
    events_by_month = defaultdict(list)
    for event in events:
        events_by_month[event.date.strftime('%B %Y')].append(event)
        
    context = {
        'events_by_month': dict(events_by_month),
    }
    
    return render(request, 'spiritual_food/liturgical_calendar.html', context)

def spiritual_directors_desk(request):
    """Spiritual director's message with enhanced content"""
    try:
        leadership_message = LeadershipMessage.objects.get(
            message_type='spiritual_director', 
            is_published=True
        )
    except LeadershipMessage.DoesNotExist:
        # Fallback to old Page model for backward compatibility
        try:
            page = Page.objects.get(slug='spiritual-directors-desk', is_published=True)
        except Page.DoesNotExist:
            page = Page(
                title="Spiritual Director's Desk",
                slug="spiritual-directors-desk",
                content="""
                <div class="prose max-w-none">
                    <h2>Spiritual Director's Desk</h2>
                    <p>Reflections from the Spiritual Director...</p>
                </div>
                """,
                is_published=True
            )
        
        context = {
            'page': page,
            'breadcrumbs': [
                ('Home', 'home'),
                ('Spiritual Food', 'spiritual_food:home'),
                ("Spiritual Director's Desk", None)
            ],
            'use_old_template': True
        }
        return render(request, 'seminary/page_detail.html', context)
    
    context = {
        'leadership_message': leadership_message,
        'breadcrumbs': [
            ('Home', 'home'),
            ('Spiritual Food', 'spiritual_food:home'),
            (leadership_message.title, None)
        ]
    }
    
    return render(request, 'seminary/leadership_message.html', context)