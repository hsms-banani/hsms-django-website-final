# seminary/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from .models import *
from .forms import ContactForm
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Rss201rev2Feed

def home(request):
    """Homepage view with featured content"""
    site_settings = SiteSettings.objects.first()
    context = {
        'site_settings': site_settings,
        'sliders': Slider.objects.filter(is_active=True).order_by('order')[:5],
        'featured_news': News.objects.filter(is_published=True, is_featured=True).order_by('-created_at')[:3],
        'upcoming_events': Event.objects.filter(
            is_published=True, 
            start_date__gte=timezone.now()
        ).order_by('start_date')[:3],
        'recent_publications': Publication.objects.filter(is_published=True).order_by('-publication_date')[:3],
        'faculty_highlights': Faculty.objects.filter(is_active=True).order_by('order')[:4],
        'current_announcements': Announcement.objects.filter(
            is_active=True,
            show_on_homepage=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).order_by('priority', '-created_at')[:2],
        'meta_description': site_settings.meta_description if site_settings else '',
        'meta_keywords': site_settings.meta_keywords if site_settings else '',
    }
    return render(request, 'seminary/home.html', context)

# Seminary Information Views
def about_seminary(request):
    """About seminary section with enhanced context"""
    
    # Fetch all the actual pages from database
    rector_message = Page.objects.filter(slug='rector-welcome', is_published=True).first()
    mission_vision = Page.objects.filter(slug='mission-vision', is_published=True).first()
    history = Page.objects.filter(slug='seminary-history', is_published=True).first()
    formation_program = Page.objects.filter(slug='formation-program', is_published=True).first()
    rules_regulations = Page.objects.filter(slug='rules-regulations', is_published=True).first()
    
    # Also try to get LeadershipMessage for rector if available
    rector_leadership = None
    try:
        rector_leadership = LeadershipMessage.objects.get(
            message_type='rector', 
            is_published=True
        )
    except LeadershipMessage.DoesNotExist:
        pass
    
    # Get actual rector faculty member
    rector_faculty = Faculty.objects.filter(
        is_active=True, 
        title__icontains='rector'
    ).first()
    
    context = {
        'page_title': 'Our Seminary',
        
        # Use actual database content
        'rector_message': rector_message,
        'rector_leadership': rector_leadership,
        'rector_faculty': rector_faculty,
        'mission_vision': mission_vision,
        'history': history,
        'formation_program': formation_program,
        'rules_regulations': rules_regulations,
        
        # Committees data - limit to show only a few on overview page
        'committees': Committee.objects.filter(is_active=True).order_by('order', 'name'),
        
        # Current announcements
        'current_announcements': Announcement.objects.filter(
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).order_by('priority', '-created_at')[:3],
        
        # Statistics
        'faculty_count': Faculty.objects.filter(is_active=True).count(),
        'committees_count': Committee.objects.filter(is_active=True).count(),
    }
    
    # If HTMX request, return partial content
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/about_seminary.html', context)
    
    return render(request, 'seminary/about_seminary.html', context)


def mission_vision(request):
    """Mission and Vision page with enhanced content"""
    page = get_object_or_404(Page, slug='mission-vision', is_published=True)
    try:
        banner = Banner.objects.get(page='about', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    
    context = {
        'page': page,
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            (page.title, None)
        ],
        'banner': banner,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/page_detail.html', context)
    
    return render(request, 'seminary/page_detail.html', context)

def seminary_history(request):
    """Seminary history page with timeline"""
    page = get_object_or_404(Page, slug='seminary-history', is_published=True)
    
    try:
        banner = Banner.objects.get(page='seminary-history', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    
    print(f"Banner for seminary-history: {banner}")
            
    # You can add historical events or milestones here
    context = {
        'page': page,
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            (page.title, None)
        ],
        'banner': banner,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/page_detail.html', context)
    
    return render(request, 'seminary/page_detail.html', context)

def formation_program(request):
    """Seminary formation program with detailed information"""
    page = get_object_or_404(Page, slug='formation-program', is_published=True)
    
    try:
        banner = Banner.objects.get(page='formation-program', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    context = {
        'page': page,
        # Fix: Use departments__slug instead of department
        'philosophy_faculty': Faculty.objects.filter(
            is_active=True, 
            departments__slug='philosophy'
        ).order_by('order')[:3],
        'theology_faculty': Faculty.objects.filter(
            is_active=True, 
            departments__slug='theology'
        ).order_by('order')[:3],
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            (page.title, None)
        ],
        'banner': banner,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/page_detail.html', context)
    
    return render(request, 'seminary/page_detail.html', context)

def rules_regulations(request):
    """Rules and regulations with categorized content"""
    page = get_object_or_404(Page, slug='rules-regulations', is_published=True)
    
    try:
        banner = Banner.objects.get(page='rules-regulations', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    context = {
        'page': page,
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            (page.title, None)
        ],
        'banner': banner,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/page_detail.html', context)
    
    return render(request, 'seminary/page_detail.html', context)

def committees(request):
    """Enhanced committees page with filtering"""
    committee_type_slug = request.GET.get('type', '')
    committees_qs = Committee.objects.filter(is_active=True).order_by('committee_type__name', 'order')
    
    if committee_type_slug:
        committees_qs = committees_qs.filter(committee_type__slug=committee_type_slug)
    
    try:
        banner = Banner.objects.get(page='committees', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    context = {
        'committees': committees_qs,
        'committee_types': CommitteeType.objects.all(),
        'selected_type': committee_type_slug,
        'page_title': 'Seminary Committees',
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            ('Committees', None)
        ],
        'banner': banner,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/committees.html', context)
    
    return render(request, 'seminary/committees.html', context)

def site_map(request):
    """Site map page"""
    
    context = {
        'pages': Page.objects.filter(is_published=True),
        'news': News.objects.filter(is_published=True),
        'events': Event.objects.filter(is_published=True),
        'publications': Publication.objects.filter(is_published=True),
        'faculty': Faculty.objects.filter(is_active=True),
        'galleries': Gallery.objects.filter(is_published=True),
    }
    return render(request, 'seminary/site_map.html', context)

# History & Heritage Views
def history_heritage(request):
    """History and heritage overview"""
    page = get_object_or_404(Page, slug='history-heritage', is_published=True)
    try:
        banner = Banner.objects.get(page='history-heritage', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None

    context = {
        'page': page,
        'banner': banner,
        'page_title': 'History & Heritage',
        'church_history': Page.objects.filter(slug='church-history', is_published=True).first(),
        'bangladesh_history': Page.objects.filter(slug='bangladesh-history', is_published=True).first(),
        'local_church_history': Page.objects.filter(slug='local-church-history', is_published=True).first(),
    }
    return render(request, 'seminary/page_detail.html', context)

def church_history(request):
    """Brief history of the Church"""
    page = get_object_or_404(Page, slug='church-history', is_published=True)
    try:
        banner = Banner.objects.get(page='church-history', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    return render(request, 'seminary/page_detail.html', {'page': page, 'banner': banner})

def bangladesh_history(request):
    """History of Bangladesh"""
    page = get_object_or_404(Page, slug='bangladesh-history', is_published=True)
    try:
        banner = Banner.objects.get(page='bangladesh-history', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    return render(request, 'seminary/page_detail.html', {'page': page, 'banner': banner})

def local_church_history(request):
    """Local Church history"""
    page = get_object_or_404(Page, slug='local-church-history', is_published=True)
    try:
        banner = Banner.objects.get(page='local-church-history', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    return render(request, 'seminary/page_detail.html', {'page': page, 'banner': banner})

# HSIT Views
def hsit_about(request):
    """HSIT About page"""
    try:
        banner = Banner.objects.get(page='hsit-about', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    context = {
        'banner': banner,
        'page_title': 'About HSIT',
        'director_message': Page.objects.filter(slug='director-message', is_published=True).first(),
        'philosophy_dept': Page.objects.filter(slug='philosophy-department', is_published=True).first(),
        'theology_dept': Page.objects.filter(slug='theology-department', is_published=True).first(),
        # Fix: Use departments__slug instead of department
        'philosophy_faculty': Faculty.objects.filter(is_active=True, departments__slug='philosophy').order_by('order'),
        'theology_faculty': Faculty.objects.filter(is_active=True, departments__slug='theology').order_by('order'),
        'administration': Faculty.objects.filter(is_active=True, departments__slug='administration').order_by('order'),
    }
    return render(request, 'seminary/hsit_about.html', context)


def rector_welcome(request):
    """Rector's welcome page with enhanced content"""
    try:
        leadership_message = LeadershipMessage.objects.get(
            message_type='rector', 
            is_published=True
        )
    except LeadershipMessage.DoesNotExist:
        # Fallback to old Page model for backward compatibility
        page = get_object_or_404(Page, slug='rector-welcome', is_published=True)
        rector = Faculty.objects.filter(
            is_active=True, 
            title__icontains='rector'
        ).first()
        
        context = {
            'page': page,
            'rector': rector,
            'breadcrumbs': [
                ('Home', 'home'),
                ('Our Seminary', 'about_seminary'),
                (page.title, None)
            ],
            'use_old_template': True
        }
        return render(request, 'seminary/rector_welcome.html', context)
    
    context = {
        'leadership_message': leadership_message,
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            (leadership_message.title, None)
        ]
    }
    
    return render(request, 'seminary/leadership_message.html', context)

def director_message(request):
    """Director's message with enhanced content"""
    try:
        leadership_message = LeadershipMessage.objects.get(
            message_type='director', 
            is_published=True
        )
    except LeadershipMessage.DoesNotExist:
        # Fallback to old Page model for backward compatibility
        try:
            page = Page.objects.get(slug='director-message', is_published=True)
        except Page.DoesNotExist:
            page = Page(
                title="Director's Message",
                slug="director-message",
                content="""
                <div class="prose max-w-none">
                    <h2>A Message from the Director</h2>
                    <p>Welcome to the Holy Spirit Major Seminary Institute of Theology (HSIT)....</p>
                </div>
                """,
                is_published=True
            )
        
        context = {
            'page': page,
            'breadcrumbs': [
                ('Home', 'home'),
                ('HSIT', 'hsit_about'),
                ("Director's Message", None)
            ],
            'use_old_template': True
        }
        return render(request, 'seminary/page_detail.html', context)
    
    context = {
        'leadership_message': leadership_message,
        'breadcrumbs': [
            ('Home', 'home'),
            ('HSIT', 'hsit_about'),
            (leadership_message.title, None)
        ]
    }
    
    return render(request, 'seminary/leadership_message.html', context)




def philosophy_department(request):
    """Philosophy department page"""
    try:
        page = Page.objects.get(slug='philosophy-department', is_published=True)
    except Page.DoesNotExist:
        page = Page(
            title="Department of Philosophy",
            slug="philosophy-department",
            content="""
            <div class="prose max-w-none">
                <h2>Department of Philosophy</h2>
                <p>The Department of Philosophy at HSIT offers a comprehensive curriculum in philosophical studies, preparing students for deeper theological understanding and critical thinking.</p>
                
                <h3>Mission</h3>
                <p>To provide foundational philosophical education that enables students to engage with fundamental questions about existence, knowledge, ethics, and human nature.</p>
                
                <h3>Curriculum</h3>
                <p>Our philosophy curriculum covers:</p>
                <ul>
                    <li>History of Philosophy</li>
                    <li>Metaphysics and Ontology</li>
                    <li>Epistemology</li>
                    <li>Ethics and Moral Philosophy</li>
                    <li>Logic and Critical Thinking</li>
                    <li>Philosophy of Religion</li>
                </ul>
            </div>
            """,
            is_published=True
        )
    
    try:
        banner = Banner.objects.get(page='philosophy-department', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    # Get faculty members from Philosophy department
    try:
        philosophy_dept = Department.objects.get(slug='philosophy')
        faculty = Faculty.objects.filter(is_active=True, departments=philosophy_dept).order_by('order')
    except Department.DoesNotExist:
        # If department doesn't exist, show all faculty for now
        faculty = Faculty.objects.filter(is_active=True).order_by('order')
    
    # Process specializations for each faculty member
    for member in faculty:
        if hasattr(member, 'specialization') and member.specialization:
            member.specializations_list = [spec.strip() for spec in member.specialization.split(',')]
        else:
            member.specializations_list = []
    
    context = {
        'page': page,
        'faculty': faculty,
        'department_name': 'Philosophy',
        'breadcrumbs': [
            ('Home', 'home'),
            ('About HSIT', 'hsit_about'),
            ('Department of Philosophy', None)
        ],
        'banner': banner,
    }
    return render(request, 'seminary/department_detail.html', context)

def theology_department(request):
    """Theology department page"""
    try:
        page = Page.objects.get(slug='theology-department', is_published=True)
    except Page.DoesNotExist:
        page = Page(
            title="Department of Theology",
            slug="theology-department",
            content="""
            <div class="prose max-w-none">
                <h2>Department of Theology</h2>
                <p>The Department of Theology at HSIT provides comprehensive theological education, preparing future priests and religious leaders for service in the Church.</p>
                
                <h3>Mission</h3>
                <p>To offer rigorous theological education rooted in Catholic tradition while engaging with contemporary challenges facing the Church and society.</p>
                
                <h3>Curriculum</h3>
                <p>Our theology curriculum includes:</p>
                <ul>
                    <li>Sacred Scripture (Old and New Testament)</li>
                    <li>Systematic Theology</li>
                    <li>Moral Theology</li>
                    <li>Church History</li>
                    <li>Liturgy and Sacraments</li>
                    <li>Canon Law</li>
                    <li>Pastoral Theology</li>
                </ul>
            </div>
            """,
            is_published=True
        )
        
    try:
        banner = Banner.objects.get(page='theology-department', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    # Get faculty members from Theology department
    try:
        theology_dept = Department.objects.get(slug='theology')
        faculty = Faculty.objects.filter(is_active=True, departments=theology_dept).order_by('order')
    except Department.DoesNotExist:
        # If department doesn't exist, show all faculty for now
        faculty = Faculty.objects.filter(is_active=True).order_by('order')
    
    # Process specializations for each faculty member
    for member in faculty:
        if hasattr(member, 'specialization') and member.specialization:
            member.specializations_list = [spec.strip() for spec in member.specialization.split(',')]
        else:
            member.specializations_list = []
    
    context = {
        'page': page,
        'faculty': faculty,
        'department_name': 'Theology',
        'breadcrumbs': [
            ('Home', 'home'),
            ('About HSIT', 'hsit_about'),
            ('Department of Theology', None)
        ],
        'banner': banner,
    }
    return render(request, 'seminary/department_detail.html', context)

def faculty_list(request):
    """Faculty listing page with pagination"""
    dept_slug = request.GET.get('dept', '')
    page_number = request.GET.get('page', 1)
    
    # Base queryset
    faculty = Faculty.objects.filter(is_active=True).order_by('order', 'name')
    
    # Filter by department if specified
    if dept_slug:
        faculty = faculty.filter(departments__slug=dept_slug)
    
    # Pagination - 12 faculty members per page (works well with 3-column grid)
    paginator = Paginator(faculty, 12)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    context = {
        'faculty_list': page_obj,
        'page_obj': page_obj,
        'departments': Department.objects.all(),
        'selected_dept': dept_slug,
        'current_params': request.GET.urlencode(),  # For preserving filters in pagination
    }
    
    # HTMX support for partial updates
    if request.htmx:
        return render(request, 'seminary/partials/faculty_list.html', context)
    
    return render(request, 'seminary/faculty.html', context)

def faculty_detail(request, pk):
    """Faculty detail page"""
    faculty = get_object_or_404(Faculty, pk=pk, is_active=True)
    
    # Get the first department of the faculty member
    first_department = faculty.departments.first()
    
    # Find related faculty members in the same department
    related_faculty = []
    if first_department:
        related_faculty = Faculty.objects.filter(
            is_active=True, 
            departments=first_department
        ).exclude(pk=pk).order_by('order')[:3]
    
    context = {
        'faculty': faculty,
        'related_faculty': related_faculty,
        'meta_description': faculty.bio[:160],
    }
    return render(request, 'seminary/faculty_detail.html', context)

from datetime import timedelta
import calendar
from datetime import date

def academic_calendar(request):
    """Academic calendar page"""
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    cal = calendar.Calendar(firstweekday=6)
    calendar_weeks = []

    events = {}
    print(f"Fetching events for {year}-{month}")
    for event in CalendarEvent.objects.filter(start_date__year=year, start_date__month=month):
        print(f"Found event: {event.title}")
        if event.start_date not in events:
            events[event.start_date] = []
        events[event.start_date].append({
            'title': event.title,
            'time': event.start_time.strftime('%I:%M %p') if event.start_time else '',
            'description': event.description
        })

    print(f"Events dictionary: {events}")

    for week in cal.monthdatescalendar(year, month):
        week_with_events = []
        for day in week:
            week_with_events.append((day, events.get(day, [])))
        calendar_weeks.append(week_with_events)

    prev_month_date = date(year, month, 1) - timedelta(days=1)
    next_month_date = date(year, month, 28) + timedelta(days=4)

    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'calendar_weeks': calendar_weeks,
        'prev_month': {'month': prev_month_date.month, 'year': prev_month_date.year},
        'next_month': {'month': next_month_date.month, 'year': next_month_date.year},
        'day_names': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    }

    return render(request, 'seminary/academic_calendar.html', context)

def course_descriptions(request):
    """Course descriptions page"""
    page = get_object_or_404(Page, slug='course-descriptions', is_published=True)
    return render(request, 'seminary/page_detail.html', {'page': page})

def library(request):
    """Library page"""
    try:
        page = Page.objects.get(slug='library', is_published=True)
    except Page.DoesNotExist:
        page = Page(
            title="Library",
            slug="library",
            content="""
            <div class="prose max-w-none">
                <h2>Library</h2>
                <p>The library at HSIT...</p>
            </div>
            """,
            is_published=True
        )
    return render(request, 'seminary/page_detail.html', {
        'page': page,
        'breadcrumbs': [
            ('Home', 'home'),
            ('About HSIT', 'hsit_about'),
            ('Library', None)
        ]
    })

def student_list(request):
    """Student list page"""
    return render(request, 'seminary/student_list.html')

def enrollment_requirements(request):
    """Enrollment requirements page"""
    page = get_object_or_404(Page, slug='enrollment-requirements', is_published=True)
    return render(request, 'seminary/page_detail.html', {'page': page})

def exam_information(request):
    """Exam information page"""
    page = get_object_or_404(Page, slug='exam-information', is_published=True)
    return render(request, 'seminary/page_detail.html', {'page': page})

def tuition_fees(request):
    """Tuition fees page"""
    page = get_object_or_404(Page, slug='tuition-fees', is_published=True)
    return render(request, 'seminary/page_detail.html', {'page': page})

def forms_documents(request):
    """Forms and documents page"""
    page = get_object_or_404(Page, slug='forms-documents', is_published=True)
    return render(request, 'seminary/page_detail.html', {'page': page})

def faqs(request):
    """FAQs page"""
    page = get_object_or_404(Page, slug='faqs', is_published=True)
    return render(request, 'seminary/page_detail.html', {'page': page})

# News & Events Views
def news_list(request):
    """News listing page"""
    news_items = News.objects.filter(is_published=True).order_by('-created_at')
    search_query = request.GET.get('q', '')
    
    if search_query:
        news_items = news_items.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query) |
            Q(excerpt__icontains=search_query)
        )
    
    paginator = Paginator(news_items, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    try:
        banner = Banner.objects.get(page='news', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'featured_news': News.objects.filter(is_published=True, is_featured=True).order_by('-created_at')[:3],
        'banner': banner,
    }
    
    if request.htmx:
        return render(request, 'seminary/partials/news_list.html', context)
    
    return render(request, 'seminary/news_list.html', context)

def news_detail(request, slug):
    """News detail page"""
    news_item = get_object_or_404(News, slug=slug, is_published=True)
    
    # Increment view count
    News.objects.filter(pk=news_item.pk).update(view_count=F('view_count') + 1)
    
    related_news = News.objects.filter(is_published=True).exclude(id=news_item.id).order_by('-created_at')[:3]
    
    context = {
        'news_item': news_item,
        'related_news': related_news,
        'meta_description': news_item.meta_description,
        'meta_keywords': news_item.tags,
    }
    return render(request, 'seminary/news_detail.html', context)

def events_list(request):
    """Events listing page"""
    now = timezone.now()
    try:
        banner = Banner.objects.get(page='events', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    
    events = Event.objects.filter(is_published=True)
    
    context = {
        'events': events,
        'upcoming_events': events.filter(start_date__gte=now)[:6],
        'past_events': events.filter(start_date__lt=now).order_by('-start_date')[:6],
        'featured_events': Event.objects.filter(is_published=True, is_featured=True, start_date__gte=now).order_by('start_date')[:3],
        'banner': banner,
    }
    return render(request, 'seminary/events.html', context)

def event_detail(request, slug):
    """Event detail page"""
    event = get_object_or_404(Event, slug=slug, is_published=True)
    related_events = Event.objects.filter(is_published=True).exclude(id=event.id).order_by('start_date')[:3]
    
    context = {
        'event': event,
        'related_events': related_events,
        'meta_description': event.description[:160],
    }
    return render(request, 'seminary/event_detail.html', context)


# Publications Views
def publications(request):
    """Publications page"""
    pub_type = request.GET.get('type', '')
    publications_qs = Publication.objects.filter(is_published=True).order_by('-publication_date')
    
    if pub_type:
        publications_qs = publications_qs.filter(publication_type=pub_type)
    
    paginator = Paginator(publications_qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    try:
        banner = Banner.objects.get(page='publications', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None

    context = {
        'page_obj': page_obj,
        'publication_types': Publication.PUBLICATION_TYPES,
        'selected_type': pub_type,
        'ankur_publications': Publication.objects.filter(is_published=True, publication_type='ankur').order_by('-publication_date')[:3],
        'diptto_publications': Publication.objects.filter(is_published=True, publication_type='diptto_sakhyo').order_by('-publication_date')[:3],
        'prodipon_publications': Publication.objects.filter(is_published=True, publication_type='prodipon').order_by('-publication_date')[:3],
        'banner': banner,
    }
    
    if request.htmx:
        return render(request, 'seminary/partials/publications_list.html', context)
    
    return render(request, 'seminary/publications.html', context)

def publication_detail(request, slug):
    """Publication detail page"""
    publication = get_object_or_404(Publication, slug=slug, is_published=True)

    # Split keywords into a clean list
    keywords = []
    if publication.keywords:
        keywords = [kw.strip() for kw in publication.keywords.split(",") if kw.strip()]

    related_publications = Publication.objects.filter(
        is_published=True,
        publication_type=publication.publication_type
    ).exclude(id=publication.id).order_by('-publication_date')[:3]
    
    context = {
        'publication': publication,
        'related_publications': related_publications,
        'keywords': keywords,  # 👈 added this
        'meta_description': publication.abstract[:160] if publication.abstract else publication.title,
        'meta_keywords': publication.keywords,
    }
    return render(request, 'seminary/publication_detail.html', context)

def download_publication(request, slug):
    """Download publication PDF"""
    publication = get_object_or_404(Publication, slug=slug, is_published=True)
    
    if publication.pdf_file:
        # Increment download count
        Publication.objects.filter(pk=publication.pk).update(download_count=F('download_count') + 1)
        
        response = HttpResponse(publication.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{publication.title}.pdf"'
        return response
    else:
        raise Http404("PDF not available")

def ankur_publications(request):
    """Ankur publications"""
    publications = Publication.objects.filter(is_published=True, publication_type='ankur').order_by('-publication_date')
    
    paginator = Paginator(publications, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'publication_type': 'ankur',
        'publication_name': 'Ankur - Student Research Papers',
    }
    return render(request, 'seminary/publication_type.html', context)

def diptto_sakhyo_publications(request):
    """Diptto Sakhyo publications"""
    publications = Publication.objects.filter(is_published=True, publication_type='diptto_sakhyo').order_by('-publication_date')
    
    paginator = Paginator(publications, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'publication_type': 'diptto_sakhyo',
        'publication_name': 'Diptto Sakhyo - Seminary Journal',
    }
    return render(request, 'seminary/publication_type.html', context)

def prodipon_publications(request):
    """Prodipon publications"""
    publications = Publication.objects.filter(is_published=True, publication_type='prodipon').order_by('-publication_date')
    
    paginator = Paginator(publications, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'publication_type': 'prodipon',
        'publication_name': 'Prodipon - Theological Journal',
    }
    return render(request, 'seminary/publication_type.html', context)

# Gallery Views
def gallery_list(request):
    """Gallery listing page"""
    gallery_type = request.GET.get('type', 'photo')
    try:
        banner = Banner.objects.get(page='gallery', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
    
    galleries = Gallery.objects.filter(is_published=True).order_by('-created_at')
    
    context = {
        'galleries': galleries,
        'gallery_types': Gallery.GALLERY_TYPES,
        'selected_type': gallery_type,
        'banner': banner,
    }
    
    if request.htmx:
        return render(request, 'seminary/partials/gallery_list.html', context)
    
    return render(request, 'seminary/gallery.html', context)

def gallery_detail(request, slug):
    """Gallery detail page"""
    gallery = get_object_or_404(Gallery, slug=slug, is_published=True)
    items = gallery.items.all().order_by('order', '-id')
    
    context = {
        'gallery': gallery,
        'items': items,
    }
    return render(request, 'seminary/gallery_detail.html', context)

def photo_gallery(request):
    """Photo gallery"""
    galleries = Gallery.objects.filter(is_published=True, gallery_type='photo').order_by('-created_at')
    
    context = {
        'galleries': galleries,
        'gallery_type': 'photo',
        'page_title': 'Photo Gallery',
    }
    return render(request, 'seminary/gallery_type.html', context)

def video_gallery(request):
    """Video gallery"""
    galleries = Gallery.objects.filter(is_published=True, gallery_type='video').order_by('-created_at')
    
    context = {
        'galleries': galleries,
        'gallery_type': 'video',
        'page_title': 'Video Gallery',
    }
    return render(request, 'seminary/gallery_type.html', context)

# Generic Views
def page_detail(request, slug):
    """Enhanced generic page detail view with dynamic breadcrumbs"""
    page = get_object_or_404(Page, slug=slug, is_published=True)
    
    # Dynamic breadcrumb generation
    breadcrumbs = [('Home', 'home')]
    
    # Seminary pages
    seminary_slugs = ['rector-welcome', 'mission-vision', 'seminary-history', 'formation-program', 'rules-regulations']
    if slug in seminary_slugs:
        breadcrumbs.append(('Our Seminary', 'about_seminary'))
    
    # HSIT pages  
    hsit_slugs = ['director-message', 'philosophy-department', 'theology-department', 'academic-calendar', 'library']
    if slug in hsit_slugs:
        breadcrumbs.append(('HSIT', 'hsit_about'))
        
    # Spiritual Food pages
    spiritual_slugs = ['prayer-services', 'homilies', 'spiritual-directors-desk']
    if slug in spiritual_slugs:
        breadcrumbs.append(('Spiritual Food', 'spiritual_food:home'))
    
    breadcrumbs.append((page.title, None))
    
    # Related pages based on parent-child relationship
    related_pages = []
    if page.parent_page:
        related_pages = Page.objects.filter(
            parent_page=page.parent_page,
            is_published=True
        ).exclude(id=page.id)[:3]
    else:
        related_pages = page.page_set.filter(is_published=True)[:3]
    
    context = {
        'page': page,
        'breadcrumbs': breadcrumbs,
        'related_pages': related_pages,
        'is_htmx': request.headers.get('HX-Request', False),
        'meta_description': page.meta_description,
        'meta_keywords': page.meta_keywords,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/page_detail.html', context)
    
    return render(request, 'seminary/page_detail.html', context)

# Contact & Communication Views
def contact(request):
    """Contact page"""
    try:
        banner = Banner.objects.get(page='contact', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            if form.send_email():
                if request.htmx:
                    return render(request, 'seminary/partials/contact_success.html')
                messages.success(request, 'Thank you for your message. We will get back to you soon!')
                return redirect('contact')
            else:
                messages.error(request, 'Sorry, there was an error sending your message. Please try again.')
        else:
            if request.htmx:
                return render(request, 'seminary/partials/contact_form.html', {'form': form, 'banner': banner})
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()
    
    context = {
        'form': form,
        'site_settings': SiteSettings.objects.first(),
        'banner': banner,
    }
    
    if request.htmx:
        return render(request, 'seminary/partials/contact_form.html', context)
    
    return render(request, 'seminary/contact.html', context)



from django.http import HttpResponse
from django.views.decorators.http import require_GET

@require_GET
@cache_page(60 * 60 * 24)  # Cache for 24 hours
def robots_txt(request):
    """
    Enhanced robots.txt for better SEO optimization
    """
    lines = [
        "# Robots.txt for Holy Spirit Major Seminary",
        "# Generated automatically - DO NOT EDIT MANUALLY",
        "",
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/search/",
        "Disallow: /load-more/",
        "Disallow: /tinymce/",
        "",
        "# Allow all other content",
        "Allow: /",
        "Allow: /static/",
        "Allow: /media/",
        "",
        "# Specific rules for major search engines",
        "User-agent: Googlebot",
        "Disallow: /admin/",
        "Disallow: /api/search/",
        "Disallow: /load-more/",
        "",
        "User-agent: Bingbot",
        "Disallow: /admin/",
        "Disallow: /api/search/",
        "Disallow: /load-more/",
        "Crawl-delay: 1",
        "",
        "# Block aggressive crawlers",
        "User-agent: AhrefsBot",
        "Disallow: /",
        "",
        "User-agent: MJ12bot",
        "Disallow: /",
        "",
        "User-agent: DotBot",
        "Disallow: /",
        "",
        "# Sitemaps",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
        "",
        "# Additional information",
        f"# Host: {request.get_host()}",
        f"# Contact: hsmsmajorseminary@gmail.com",
        f"# Last updated: {request.META.get('HTTP_DATE', 'Unknown')}",
    ]
    
    return HttpResponse(
        "\n".join(lines), 
        content_type="text/plain; charset=utf-8",
        headers={
            'Cache-Control': 'public, max-age=86400',  # Cache for 1 day
        }
    )

# Search & HTMX Views

@require_GET
def search(request):
    """HTMX search functionality"""
    query = request.GET.get('q', '').strip()
    print(f"Search query: {query}")
    
    if not query or len(query) < 2:
        return render(request, 'seminary/partials/search_results.html', {'results': []})
    
    results = []
    
    # Search news
    news_results = News.objects.filter(
        Q(title__icontains=query) | Q(content__icontains=query) | Q(excerpt__icontains=query),
        is_published=True
    ).order_by('-created_at')
    results.extend(news_results)
    
    # Search pages
    page_results = Page.objects.filter(
        Q(title__icontains=query) | Q(content__icontains=query),
        is_published=True
    )
    results.extend(page_results)
    
    # Search events
    event_results = Event.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query),
        is_published=True
    ).order_by('-start_date')
    results.extend(event_results)
    
    # Search faculty
    faculty_results = Faculty.objects.filter(
        Q(name__icontains=query) | Q(title__icontains=query) | Q(bio__icontains=query),
        is_active=True
    )
    results.extend(faculty_results)
    
    # Search publications
    publication_results = Publication.objects.filter(
        Q(title__icontains=query) | Q(author__icontains=query) | Q(content__icontains=query),
        is_published=True
    ).order_by('-publication_date')
    results.extend(publication_results)
    
    print(f"Search results: {results}")

    if request.htmx:
        return render(request, 'seminary/partials/search_results.html', {'results': results, 'query': query})
    
    return render(request, 'seminary/search.html', {'results': results, 'query': query})

@require_GET
def quick_search(request):
    """Quick search for autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    results = []
    
    # Quick search in titles only
    news_results = News.objects.filter(title__icontains=query, is_published=True)[:3]
    for news in news_results:
        results.append({'title': news.title, 'url': news.get_absolute_url(), 'type': 'News'})
    
    event_results = Event.objects.filter(title__icontains=query, is_published=True)[:3]
    for event in event_results:
        results.append({'title': event.title, 'url': event.get_absolute_url(), 'type': 'Event'})
    
    page_results = Page.objects.filter(title__icontains=query, is_published=True)[:3]
    for page in page_results:
        results.append({'title': page.title, 'url': page.get_absolute_url(), 'type': 'Page'})
    
    return JsonResponse({'results': results})

def load_more_news(request):
    """Load more news via HTMX"""
    page = request.GET.get('page', 1)
    news_items = News.objects.filter(is_published=True).order_by('-created_at')
    
    paginator = Paginator(news_items, 6)
    page_obj = paginator.get_page(page)
    
    context = {'page_obj': page_obj}
    return render(request, 'seminary/partials/news_items.html', context)

def load_more_events(request):
    """Load more events via HTMX"""
    page = request.GET.get('page', 1)
    events = Event.objects.filter(is_published=True).order_by('start_date')
    
    paginator = Paginator(events, 6)
    page_obj = paginator.get_page(page)
    
    context = {'page_obj': page_obj}
    return render(request, 'seminary/partials/event_items.html', context)

# API Views
@require_GET
def api_announcements(request):
    """API endpoint for current announcements"""
    announcements = Announcement.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).order_by('priority', '-created_at')[:5]
    
    data = []
    for announcement in announcements:
        data.append({
            'title': announcement.title,
            'content': announcement.content,
            'priority': announcement.priority,
            'target_audience': announcement.target_audience,
        })
    
    return JsonResponse({'announcements': data})

@require_GET
def api_upcoming_events(request):
    """API endpoint for upcoming events"""
    events = Event.objects.filter(
        is_published=True,
        start_date__gte=timezone.now()
    ).order_by('start_date')[:10]
    
    data = []
    for event in events:
        data.append({
            'title': event.title,
            'start_date': event.start_date.isoformat(),
            'end_date': event.end_date.isoformat() if event.end_date else None,
            'location': event.location,
            'url': event.get_absolute_url(),
        })
    
    return JsonResponse({'events': data})


def history_heritage(request):
    """Main History & Heritage page"""
    try:
        page = Page.objects.get(slug='history-heritage', is_published=True)
    except Page.DoesNotExist:
        # Create a default page if it doesn't exist
        page = Page(
            title="History & Heritage",
            slug="history-heritage",
            content="""
            <div class="prose max-w-none">
                <p class="lead">Explore the rich history and heritage of the Catholic Church, Bangladesh, and our local Church community.</p>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                    <div class="text-center">
                        <i class="fas fa-church text-4xl text-blue-600 mb-4"></i>
                        <h3 class="text-xl font-semibold mb-2">Church History</h3>
                        <p>Discover the 2000-year journey of the Catholic Church from apostolic times to the present day.</p>
                    </div>
                    <div class="text-center">
                        <i class="fas fa-flag text-4xl text-green-600 mb-4"></i>
                        <h3 class="text-xl font-semibold mb-2">Bangladesh History</h3>
                        <p>Learn about the rich cultural and religious heritage of Bangladesh and its people.</p>
                    </div>
                    <div class="text-center">
                        <i class="fas fa-home text-4xl text-red-600 mb-4"></i>
                        <h3 class="text-xl font-semibold mb-2">Local Church History</h3>
                        <p>Explore the history of the Catholic Church in Bangladesh and our local diocese.</p>
                    </div>
                </div>
            </div>
            """,
            is_published=True
        )
    
    try:
        banner = Banner.objects.get(page='history-heritage', is_active=True)
    except Banner.DoesNotExist:
        try:
            banner = Banner.objects.get(page='default-banner', is_active=True)
        except Banner.DoesNotExist:
            banner = None
            
    return render(request, 'seminary/page_detail.html', {
        'page': page,
        'breadcrumbs': [
            ('Home', 'home'),
            ('History & Heritage', None)
        ],
        'banner': banner,
    })








def terms_of_service(request):
    """Display Terms of Service page"""
    return render(request, 'seminary/terms_of_service.html')

def privacy_policy(request):
    """Display Privacy Policy page"""
    return render(request, 'seminary/privacy_policy.html')


class NewsFeed(Feed):
    title = "Holy Spirit Major Seminary - Latest News"
    link = "/news/"
    description = "Latest news and updates from Holy Spirit Major Seminary"
    feed_type = Rss201rev2Feed

    def items(self):
        return News.objects.filter(is_published=True).order_by('-created_at')[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.content[:200]

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        return item.created_at
    

def seminary_administration(request):
    """Seminary Administration page with HTMX filtering"""
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'order')  # Default sort by order
    
    # Base queryset
    administrators = SeminaryAdministration.objects.filter(is_active=True)
    
    # Apply search filter
    if search_query:
        administrators = administrators.filter(
            Q(name__icontains=search_query) | 
            Q(designation__icontains=search_query) |
            Q(bio__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'name':
        administrators = administrators.order_by('name')
    elif sort_by == 'designation':
        administrators = administrators.order_by('designation', 'name')
    elif sort_by == 'start_date':
        administrators = administrators.order_by('-start_date', 'order')
    else:  # default to order
        administrators = administrators.order_by('order', 'name')
    
    # Get statistics
    total_administrators = SeminaryAdministration.objects.filter(is_active=True).count()
    
    context = {
        'administrators': administrators,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_administrators': total_administrators,
        'page_title': 'Seminary Administration',
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            ('Seminary Administration', None)
        ],
        'sort_options': [
            ('order', 'Display Order'),
            ('name', 'Name'),
            ('designation', 'Designation'),
            ('start_date', 'Start Date'),
        ]
    }
    
    # Return partial template for HTMX requests
    if request.headers.get('HX-Request'):
        return render(request, 'seminary/partials/administration_list.html', context)
    
    return render(request, 'seminary/seminary_administration.html', context)

def administration_detail(request, pk):
    """Individual administrator detail page"""
    administrator = get_object_or_404(SeminaryAdministration, pk=pk, is_active=True)
    
    # Get related administrators (same level or similar designation)
    related_administrators = SeminaryAdministration.objects.filter(
        is_active=True
    ).exclude(pk=pk).order_by('order')[:3]
    
    context = {
        'administrator': administrator,
        'related_administrators': related_administrators,
        'page_title': f"{administrator.name} - {administrator.designation}",
        'breadcrumbs': [
            ('Home', 'home'),
            ('Our Seminary', 'about_seminary'),
            ('Seminary Administration', 'seminary_administration'),
            (administrator.name, None)
        ],
        'meta_description': f"{administrator.name}, {administrator.designation} at Holy Spirit Major Seminary. {administrator.bio[:120] if administrator.bio else ''}",
    }
    
    return render(request, 'seminary/administration_detail.html', context)

@require_GET
def administration_filter(request):
    """HTMX endpoint for filtering administrators"""
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'order')
    
    administrators = SeminaryAdministration.objects.filter(is_active=True)
    
    if search_query:
        administrators = administrators.filter(
            Q(name__icontains=search_query) | 
            Q(designation__icontains=search_query) |
            Q(bio__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'name':
        administrators = administrators.order_by('name')
    elif sort_by == 'designation':
        administrators = administrators.order_by('designation', 'name')
    elif sort_by == 'start_date':
        administrators = administrators.order_by('-start_date', 'order')
    else:
        administrators = administrators.order_by('order', 'name')
    
    context = {
        'administrators': administrators,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    
    return render(request, 'seminary/partials/administration_list.html', context)