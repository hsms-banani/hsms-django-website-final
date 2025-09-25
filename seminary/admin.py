# seminary/admin.py - Updated with TinyMCE
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from tinymce.widgets import TinyMCE
from django import forms
from .models import *

# Custom forms with TinyMCE widgets
class PageAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
    excerpt = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 10}), required=False)
    
    class Meta:
        model = Page
        fields = '__all__'

class NewsAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
    
    class Meta:
        model = News
        fields = '__all__'

class EventAdminForm(forms.ModelForm):
    description = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 20}))
    
    class Meta:
        model = Event
        fields = '__all__'

class PublicationAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
    abstract = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 10}), required=False)
    
    class Meta:
        model = Publication
        fields = '__all__'

class FacultyAdminForm(forms.ModelForm):
    bio = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 20}))
    qualifications = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 10}), required=False)
    
    class Meta:
        model = Faculty
        fields = '__all__'

class CommitteeAdminForm(forms.ModelForm):
    description = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 15}))
    responsibilities = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 15}), required=False)
    
    class Meta:
        model = Committee
        fields = '__all__'

class AnnouncementAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 15}))
    
    class Meta:
        model = Announcement
        fields = '__all__'

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'site_motto', 'email', 'phone')
    fieldsets = (
        ('Basic Information', {
            'fields': ('site_name', 'site_motto', 'site_logo', 'hsit_logo')
        }),
        ('Contact Information', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'youtube_url')
        }),
        ('SEO & Analytics', {
            'fields': ('google_analytics_id', 'meta_description', 'meta_keywords')
        }),
    )
    
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm
    list_display = ('title', 'slug', 'is_published', 'show_in_menu', 'parent_page', 'order', 'created_at')
    list_filter = ('is_published', 'show_in_menu', 'parent_page', 'created_at')
    search_fields = ('title', 'content', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published', 'show_in_menu', 'order')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug')
        }),
        ('Content', {
            'fields': ('excerpt', 'content'),
            'classes': ('wide',)
        }),
        ('Organization', {
            'fields': ('parent_page', 'order', 'show_in_menu')
        }),
        ('Media & SEO', {
            'fields': ('featured_image', 'meta_description', 'meta_keywords')
        }),
        ('Publishing', {
            'fields': ('is_published', 'author')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['make_published', 'make_unpublished', 'duplicate_page']
    
    def make_published(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} pages were successfully published.')
    make_published.short_description = "Mark selected pages as published"
    
    def make_unpublished(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} pages were successfully unpublished.')
    make_unpublished.short_description = "Mark selected pages as unpublished"
    
    def duplicate_page(self, request, queryset):
        for page in queryset:
            page.pk = None
            page.slug = f"{page.slug}-copy"
            page.title = f"{page.title} (Copy)"
            page.is_published = False
            page.save()
        self.message_user(request, f'{queryset.count()} pages were successfully duplicated.')
    duplicate_page.short_description = "Duplicate selected pages"



class LeadershipMessageAdminForm(forms.ModelForm):
    message_content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
    
    class Meta:
        model = LeadershipMessage
        fields = '__all__'

@admin.register(LeadershipMessage)
class LeadershipMessageAdmin(admin.ModelAdmin):
    form = LeadershipMessageAdminForm
    list_display = ('message_type', 'leader_name', 'leader_title', 'is_published', 'updated_at')
    list_filter = ('message_type', 'is_published', 'created_at')
    search_fields = ('leader_name', 'leader_title', 'message_content')
    list_editable = ('is_published',)
    
    fieldsets = (
        ('Message Type & Basic Info', {
            'fields': ('message_type', 'title')
        }),
        ('Leader Information', {
            'fields': ('leader_name', 'leader_title', 'leader_photo'),
            'classes': ('wide',)
        }),
        ('Content', {
            'fields': ('message_content', 'quote'),
            'classes': ('wide',)
        }),
        ('Visual Elements', {
            'fields': ('background_image',),
            'classes': ('collapse',)
        }),
        ('SEO & Publishing', {
            'fields': ('meta_description', 'meta_keywords', 'is_published', 'author'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion to maintain the two required message types
        if obj and LeadershipMessage.objects.count() <= 2:
            return False
        return super().has_delete_permission(request, obj)
    
    actions = ['make_published', 'make_unpublished']
    
    def make_published(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} leadership messages were successfully published.')
    make_published.short_description = "Mark selected messages as published"
    
    def make_unpublished(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} leadership messages were successfully unpublished.')
    make_unpublished.short_description = "Mark selected messages as unpublished"


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    form = FacultyAdminForm
    list_display = ('name', 'title', 'display_departments', 'is_active', 'order')
    list_filter = ('departments', 'is_active')
    search_fields = ('name', 'title', 'specialization')
    list_editable = ('order', 'is_active')
    filter_horizontal = ('departments',)
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'title', 'photo')
        }),
        ('Academic Information', {
            'fields': ('departments', 'specialization')
        }),
        ('Qualifications', {
            'fields': ('qualifications',),
            'classes': ('wide',)
        }),
        ('Biography', {
            'fields': ('bio',),
            'classes': ('wide',)
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'office_hours')
        }),
        ('Settings', {
            'fields': ('order', 'is_active', 'joined_date')
        }),
    )

    def display_departments(self, obj):
        return ", ".join([dept.name for dept in obj.departments.all()])
    display_departments.short_description = 'Departments'

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    form = NewsAdminForm
    list_display = ('title', 'is_featured', 'is_published', 'view_count', 'created_at')
    list_filter = ('is_featured', 'is_published', 'created_at')
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_featured', 'is_published')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'excerpt', 'featured_image')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured', 'publish_date', 'author')
        }),
        ('SEO', {
            'fields': ('meta_description', 'tags')
        }),
        ('Statistics', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    form = EventAdminForm
    list_display = ('title', 'start_date', 'end_date', 'location', 'event_type', 'is_featured', 'is_published')
    list_filter = ('event_type', 'is_featured', 'is_published', 'start_date')
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_featured', 'is_published')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'slug', 'featured_image', 'event_type')
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('wide',)
        }),
        ('Schedule & Location', {
            'fields': ('start_date', 'end_date', 'location')
        }),
        ('Contact & Registration', {
            'fields': ('organizer', 'contact_email', 'contact_phone', 'registration_required', 'registration_deadline', 'max_participants')
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured')
        }),
    )

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    form = PublicationAdminForm
    list_display = ('title', 'publication_type', 'author', 'publication_date', 'download_count', 'is_published')
    list_filter = ('publication_type', 'is_published', 'publication_date')
    search_fields = ('title', 'author', 'abstract', 'keywords')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published',)
    date_hierarchy = 'publication_date'
    
    fieldsets = (
        ('Publication Details', {
            'fields': ('title', 'slug', 'publication_type', 'cover_image')
        }),
        ('Abstract', {
            'fields': ('abstract',),
            'classes': ('wide',)
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Author Information', {
            'fields': ('author', 'co_authors')
        }),
        ('Publication Info', {
            'fields': ('publication_date', 'volume', 'issue', 'page_numbers')
        }),
        ('Files & Media', {
            'fields': ('pdf_file',)
        }),
        ('Metadata', {
            'fields': ('keywords', 'is_published', 'download_count')
        }),
    )

@admin.register(CommitteeMember)
class CommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'designation', 'email', 'phone')
    search_fields = ('name', 'designation')


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ('name', 'committee_type', 'advisor', 'is_active', 'established_date')
    list_filter = ('committee_type', 'is_active', 'established_date')
    search_fields = ('name', 'description')
    filter_horizontal = ('members',)
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'committee_type')
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('wide',)
        }),
        ('Responsibilities', {
            'fields': ('responsibilities',),
            'classes': ('wide',)
        }),
        ('Leadership & Members', {
            'fields': ('advisor', 'members')
        }),
        ('Settings', {
            'fields': ('established_date', 'is_active', 'order')
        }),
    )



@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementAdminForm
    list_display = ('title', 'priority', 'target_audience', 'is_active', 'show_on_homepage', 'start_date', 'end_date')
    list_filter = ('priority', 'target_audience', 'is_active', 'show_on_homepage', 'start_date')
    search_fields = ('title', 'content')
    list_editable = ('is_active', 'show_on_homepage')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title',)
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Settings', {
            'fields': ('priority', 'target_audience', 'is_active', 'show_on_homepage')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date')
        }),
    )

# Keep existing admin classes for other models
@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'gallery_type', 'is_published', 'created_at')
    list_filter = ('gallery_type', 'is_published', 'created_at')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published',)

class GalleryItemInline(admin.TabularInline):
    model = GalleryItem
    extra = 3
    fields = ('title', 'image', 'video_url', 'description', 'order')

@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'gallery', 'order', 'uploaded_at')
    list_filter = ('gallery', 'uploaded_at')
    search_fields = ('title', 'description')

@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'start_date', 'end_date')
    list_filter = ('is_active', 'text_position', 'button_style')
    search_fields = ('title', 'subtitle')
    list_editable = ('order', 'is_active')
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'subtitle', 'link_url', 'link_text')
        }),
        ('Images', {
            'fields': ('image', 'mobile_image')
        }),
        ('Styling', {
            'fields': ('text_position', 'button_style', 'overlay_opacity')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date', 'is_active', 'order')
        }),
    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

# Customize admin site headers
admin.site.site_header = "Holy Spirit Major Seminary Administration"
admin.site.site_title = "HSMS Admin"
admin.site.index_title = "Welcome to HSMS Administration"

# Add custom CSS for better TinyMCE integration in admin
class Media:
    css = {
        'all': ('css/tinymce-content.css',)
    }


class SeminaryAdministrationAdminForm(forms.ModelForm):
    bio = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 15}), required=False)
    
    class Meta:
        model = SeminaryAdministration
        fields = '__all__'

@admin.register(SeminaryAdministration)
class SeminaryAdministrationAdmin(admin.ModelAdmin):
    form = SeminaryAdministrationAdminForm
    list_display = ('name', 'designation', 'email', 'phone', 'is_active', 'order')
    list_filter = ('is_active', 'start_date', 'created_at')
    search_fields = ('name', 'designation', 'email')
    list_editable = ('order', 'is_active')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'designation', 'photo'),
            'classes': ('wide',)
        }),
        ('Biography', {
            'fields': ('bio',),
            'classes': ('wide', 'collapse')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'office_location', 'office_hours'),
            'classes': ('wide',)
        }),
        ('Administrative Details', {
            'fields': ('start_date', 'order', 'is_active'),
            'classes': ('wide',)
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'duplicate_administrator']
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} administrators were successfully activated.')
    make_active.short_description = "Mark selected administrators as active"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} administrators were successfully deactivated.')
    make_inactive.short_description = "Mark selected administrators as inactive"
    
    def duplicate_administrator(self, request, queryset):
        for admin_obj in queryset:
            admin_obj.pk = None
            admin_obj.name = f"{admin_obj.name} (Copy)"
            admin_obj.is_active = False
            admin_obj.save()
        self.message_user(request, f'{queryset.count()} administrators were successfully duplicated.')
    duplicate_administrator.short_description = "Duplicate selected administrators"
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ['created_at', 'updated_at']
        return []