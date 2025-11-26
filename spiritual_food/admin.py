# spiritual_food/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Announcement, PrayerService, HomilyCategory, 
    Homily, PrayerRequest, DonationInfo, PrayerRequestSettings, LiturgicalCalendar, Saint
)

@admin.register(Saint)
class SaintAdmin(admin.ModelAdmin):
    list_display = ('name', 'feast_day')
    search_fields = ('name',)

@admin.register(LiturgicalCalendar)
class LiturgicalCalendarAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'rank', 'color', 'is_holy_day_of_obligation']
    list_filter = ['rank', 'season', 'color', 'is_holy_day_of_obligation', 'date']
    search_fields = ['name', 'first_reading', 'responsorial_psalm', 'second_reading', 'gospel']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('name', 'date', 'season', 'rank', 'color', 'is_holy_day_of_obligation')
        }),
        ('Readings', {
            'fields': ('cycle', 'first_reading', 'responsorial_psalm', 'second_reading', 'gospel'),
            'classes': ('collapse',)
        }),
        ('Saints', {
            'fields': ('saints',),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ('saints',)



@admin.register(PrayerRequestSettings)
class PrayerRequestSettingsAdmin(admin.ModelAdmin):
    """Admin view for PrayerRequestSettings"""
    
    fieldsets = (
        ('Email Notifications', {
            'fields': ('send_email_notifications', 'notification_email'),
            'description': 'Configure email alerts for new prayer requests.'
        }),
        ('Prayer Request Management', {
            'fields': ('keep_a_copy',),
            'description': 'Decide whether to store a copy of each prayer request.'
        }),
    )

    def has_add_permission(self, request):
        # Prevent creating more than one settings object
        return not PrayerRequestSettings.objects.exists()



@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'content_type', 'is_active', 'priority', 'created_at', 'expires_at']
    list_filter = ['is_active', 'content_type', 'created_at']
    search_fields = ['title', 'short_description']
    list_editable = ['is_active', 'priority']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'short_description', 'content_type')
        }),
        ('Content', {
            'fields': ('text_content', 'pdf_file', 'image_file'),
            'description': 'Add content based on the selected content type'
        }),
        ('Display Settings', {
            'fields': ('is_active', 'priority', 'expires_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['created_at', 'updated_at']
        return []


@admin.register(PrayerService)
class PrayerServiceAdmin(admin.ModelAdmin):
    list_display = ['service_name', 'service_type', 'day', 'time', 'location', 'is_active', 'order']
    list_filter = ['service_type', 'day', 'is_active']
    search_fields = ['service_name', 'description', 'location']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'day', 'time']
    
    fieldsets = (
        ('Service Information', {
            'fields': ('service_name', 'service_type', 'description')
        }),
        ('Schedule', {
            'fields': ('day', 'time', 'location')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(HomilyCategory)
class HomilyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    list_editable = ['order']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Homily)
class HomilyAdmin(admin.ModelAdmin):
    list_display = ['title', 'preacher', 'date', 'liturgical_season', 'is_featured', 'is_published', 'views_count']
    list_filter = ['is_featured', 'is_published', 'liturgical_season', 'date', 'category']
    search_fields = ['title', 'preacher', 'scripture_reference', 'tags']
    list_editable = ['is_featured', 'is_published']
    date_hierarchy = 'date'
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'preacher', 'date', 'category', 'tags')
        }),
        ('Liturgical Information', {
            'fields': ('liturgical_season', 'sunday_reading', 'scripture_reference')
        }),
        ('Content', {
            'fields': ('summary', 'text_content', 'youtube_url', 'thumbnail')
        }),
        ('Publishing', {
            'fields': ('is_featured', 'is_published', 'views_count')
        }),
    )
    
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['created_at', 'updated_at']
        return self.readonly_fields


@admin.register(PrayerRequest)
class PrayerRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'request_type', 'status', 'make_public', 'created_at', 'view_button']
    list_filter = ['status', 'request_type', 'make_public', 'wants_to_donate', 'created_at']
    search_fields = ['name', 'email', 'phone', 'intention']
    list_editable = ['status']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Requester Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Request Details', {
            'fields': ('request_type', 'intention', 'preferred_date', 'make_public')
        }),
        ('Donation Information', {
            'fields': ('wants_to_donate', 'donation_amount', 'donation_reference'),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('status', 'admin_notes', 'created_at', 'updated_at')
        }),
    )
    
    def view_button(self, obj):
        return format_html(
            '<a class="button" href="{}">View</a>',
            reverse('admin:spiritual_food_prayerrequest_change', args=[obj.pk])
        )
    view_button.short_description = 'Actions'


@admin.register(DonationInfo)
class DonationInfoAdmin(admin.ModelAdmin):
    list_display = ['payment_method', 'account_name', 'account_number', 'is_active', 'order']
    list_filter = ['payment_method', 'is_active']
    search_fields = ['account_name', 'account_number', 'bank_name']
    list_editable = ['is_active', 'order']
    
    fieldsets = (
        ('Payment Method', {
            'fields': ('payment_method', 'account_name', 'account_number')
        }),
        ('Bank Details (if applicable)', {
            'fields': ('bank_name', 'branch_name', 'routing_number', 'swift_code'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('instructions', 'qr_code')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order')
        }),
    )