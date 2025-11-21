# library/admin.py - Enhanced with Borrowing System

from django.contrib import admin, messages
from django.utils.html import format_html
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from .models import Category, Publisher, Author, Book, BookSearch, BorrowRecord, LibrarySetting
from .email_service import LibraryEmailService
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import LibraryUser
from django.http import HttpResponse
from django.utils.html import format_html
from .models import LibraryUser, BulkUserImportLog
from .utils import process_bulk_user_csv, generate_credentials_csv
from .models import BorrowRecord, LibraryPasswordSettings
from .email_service import LibraryEmailService
import csv

class LibraryUserCreationForm(UserCreationForm):
    class Meta:
        model = LibraryUser
        fields = ('username', 'email', 'first_name', 'last_name', 'is_staff')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user



@admin.register(LibraryUser)
class LibraryUserAdmin(UserAdmin):
    """Admin interface for library users only"""
    add_form = LibraryUserCreationForm
    
    list_display = ('username', 'email', 'full_name', 'is_active', 'is_staff', 'date_joined', 'last_login')
    list_filter = ('is_active', 'is_staff', 'date_joined', 'last_login')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'default_password', 'email', 'first_name', 'last_name', 'is_staff'),
        }),
    )
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    readonly_fields = ('last_login', 'date_joined')
    
    def get_queryset(self, request):
        """Show all users"""
        return super().get_queryset(request)
    
    def save_model(self, request, obj, form, change):
        """Set default password for new users"""
        if not change:  # New user
            password_settings = LibraryPasswordSettings.objects.first()
            if password_settings:
                obj.set_password(password_settings.default_password)
            else:
                # Fallback if no default password is set
                obj.set_password(User.objects.make_random_password())
        
        super().save_model(request, obj, form, change)
    
    
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "-"
    full_name.short_description = 'Name'
    
    # Add custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-template/', self.admin_site.admin_view(self.download_template), 
                 name='library_libraryuser_download_template'),
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), 
                 name='library_libraryuser_bulk_upload'),
            path('bulk-upload/process/', self.admin_site.admin_view(self.process_bulk_upload), 
                 name='library_libraryuser_process_upload'),
        ]
        return custom_urls + urls
    
    def download_template(self, request):
        """Download CSV template for bulk user creation"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="library_users_template.csv"'
        
        # Add BOM for Excel UTF-8 compatibility
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Header with instructions
        writer.writerow(['# Library Users Bulk Upload Template'])
        writer.writerow(['# Instructions:'])
        writer.writerow(['# 1. Fill in the required fields: first_name, last_name, email'])
        writer.writerow(['# 2. username is optional - will be auto-generated if not provided'])
        writer.writerow(['# 3. Email and username must be unique.'])
        writer.writerow(['# 4. Save the file and upload through the admin panel'])
        writer.writerow(['# 5. Delete these instruction rows before uploading'])
        writer.writerow(['# 6. The file must be comma-separated (.csv)'])
        writer.writerow([])
        
        # Actual header
        writer.writerow(['first_name*', 'last_name*', 'email*', 'username'])
        
        # Sample data
        writer.writerow(['John', 'Doe', 'john.doe@example.com', ''])
        writer.writerow(['Jane', 'Smith', 'jane.smith@example.com', 'jsmith'])
        writer.writerow(['রহিম', 'আহমেদ', 'rahim.ahmed@example.com', ''])
        
        return response
    
    def bulk_upload_view(self, request):
        """Render bulk upload form"""
        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk Upload Library Users',
        }
        return render(request, 'admin/library/bulk_upload_form.html', context)
    
    def process_bulk_upload(self, request):
        """Process the uploaded CSV file"""
        if request.method != 'POST':
            return redirect('admin:library_libraryuser_bulk_upload')
        
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('admin:library_libraryuser_bulk_upload')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('admin:library_libraryuser_bulk_upload')
        
        try:
            # Process the CSV
            result = process_bulk_user_csv(csv_file, request.user)
            
            # Store credentials in session for download
            request.session['bulk_user_credentials'] = result['created_users']
            
            # Show summary
            if result['successful_imports'] > 0:
                messages.success(
                    request, 
                    f"Successfully created {result['successful_imports']} users out of {result['total_records']} records."
                )
            
            if result['failed_imports'] > 0:
                messages.warning(
                    request,
                    f"{result['failed_imports']} records failed. Check the import log for details."
                )
            
            # Redirect to download credentials page
            return redirect('admin:library_libraryuser_download_credentials', 
                          import_id=result['import_log'].id)
            
        except UnicodeDecodeError:
            messages.error(request, "Error processing CSV file: The file is not properly encoded. Please save it as UTF-8.")
        except ValidationError as e:
            messages.error(request, f"Error processing CSV file: {e.message}")
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {str(e)}')
        
        return redirect('admin:library_libraryuser_bulk_upload')
    
    # Add download credentials URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-template/', self.admin_site.admin_view(self.download_template), 
                 name='library_libraryuser_download_template'),
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), 
                 name='library_libraryuser_bulk_upload'),
            path('bulk-upload/process/', self.admin_site.admin_view(self.process_bulk_upload), 
                 name='library_libraryuser_process_upload'),
            path('download-credentials/<int:import_id>/', 
                 self.admin_site.admin_view(self.download_credentials), 
                 name='library_libraryuser_download_credentials'),
            path('download-credentials-file/<int:import_id>/', 
                 self.admin_site.admin_view(self.download_credentials_file), 
                 name='library_libraryuser_download_credentials_file'),
        ]
        return custom_urls + urls
    
    def download_credentials(self, request, import_id):
        """Display a page with a button to download the credentials CSV file."""
        import_log = get_object_or_404(BulkUserImportLog, id=import_id)
        context = {
            **self.admin_site.each_context(request),
            'title': 'Download Credentials',
            'import_id': import_id,
        }
        return render(request, 'admin/library/download_credentials.html', context)

    def download_credentials_file(self, request, import_id):
        """Download credentials for recently created users"""
        import_log = get_object_or_404(BulkUserImportLog, id=import_id)
        users_data = request.session.get('bulk_user_credentials', [])
        
        if not users_data:
            messages.error(request, 'No credentials available for download.')
            return redirect('admin:library_libraryuser_changelist')
        
        # Generate CSV
        csv_content = generate_credentials_csv(users_data)
        
        # Create response
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
        filename = f"library_users_credentials_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Clear session data
        del request.session['bulk_user_credentials']
        
        messages.success(request, 'Credentials downloaded successfully. Please store this file securely!')
        
        return response

    
    def changelist_view(self, request, extra_context=None):
        """Add custom buttons to the changelist"""
        extra_context = extra_context or {}
        extra_context['show_bulk_upload'] = True
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(LibraryPasswordSettings)
class LibraryPasswordSettingsAdmin(admin.ModelAdmin):
    """Admin interface for library password settings"""
    list_display = ('__str__',)

    def has_add_permission(self, request):
        return not LibraryPasswordSettings.objects.exists()



@admin.register(BulkUserImportLog)
class BulkUserImportLogAdmin(admin.ModelAdmin):
    """Admin for viewing bulk import logs"""
    list_display = ('import_date', 'imported_by', 'total_records', 
                    'successful_imports', 'failed_imports', 'view_details')
    list_filter = ('import_date', 'imported_by')
    search_fields = ('imported_by__username', 'error_log', 'success_log')
    readonly_fields = ('imported_by', 'import_date', 'csv_file', 'total_records',
                      'successful_imports', 'failed_imports', 'error_log_display', 
                      'success_log_display')
    
    fieldsets = (
        ('Import Details', {
            'fields': ('imported_by', 'import_date', 'csv_file')
        }),
        ('Statistics', {
            'fields': ('total_records', 'successful_imports', 'failed_imports')
        }),
        ('Success Log', {
            'fields': ('success_log_display',),
            'classes': ('collapse',)
        }),
        ('Error Log', {
            'fields': ('error_log_display',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def error_log_display(self, obj):
        if obj.error_log and obj.error_log != 'No errors':
            return format_html('<pre style="background: #f8d7da; padding: 10px; border-radius: 4px;">{}</pre>', 
                             obj.error_log)
        return "No errors"
    error_log_display.short_description = 'Error Log'
    
    def success_log_display(self, obj):
        if obj.success_log and obj.success_log != 'No successful imports':
            return format_html('<pre style="background: #d4edda; padding: 10px; border-radius: 4px;">{}</pre>', 
                             obj.success_log)
        return "No successful imports"
    success_log_display.short_description = 'Success Log'
    
    def view_details(self, obj):
        return format_html(
            '<a class="button" href="{}">View Details</a>',
            reverse('admin:library_bulkuserimportlog_change', args=[obj.pk])
        )
    view_details.short_description = 'Actions'


admin.site.unregister(User)
admin.site.register(User, LibraryUserAdmin)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_bangla', 'description', 'book_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'name_bangla', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def book_count(self, obj):
        return obj.book_publications.count()
    book_count.short_description = 'Books'

@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_bangla', 'website', 'established_year', 'book_count', 'created_at']
    list_filter = ['established_year', 'created_at']
    search_fields = ['name', 'name_bangla', 'address']
    prepopulated_fields = {'slug': ('name',)}
    
    def book_count(self, obj):
        return obj.book_publications.count()
    book_count.short_description = 'Books Published'

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'full_name_bangla', 'nationality', 'birth_year', 'death_year', 'book_count']
    list_filter = ['nationality', 'birth_year', 'primary_language']
    search_fields = ['first_name', 'last_name', 'first_name_bangla', 'last_name_bangla', 'bio']
    prepopulated_fields = {'slug': ('first_name', 'last_name')}
    
    def book_count(self, obj):
        return obj.publications.count()
    book_count.short_description = 'Books Written'

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'accession_number', 'volume', 'authors_display', 'publisher', 
        'publication_year', 'call_number', 'category', 'availability_status', 
        'times_borrowed'
    ]
    list_filter = [
        'status', 'category', 'language', 'publication_year', 
        'publisher', 'acquisition_date'
    ]
    search_fields = [
        'title', 'title_bangla', 'subtitle', 'accession_number', 'volume',
        'isbn_10', 'isbn_13', 'call_number', 'classification_number', 
        'cutter_number', 'keywords', 'authors__first_name', 'authors__last_name'
    ]
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['authors']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'title_bangla', 'subtitle', 'subtitle_bangla', 
                      'slug', 'authors', 'publisher', 'publication_year')
        }),
        ('Identification & Classification', {
            'fields': ('accession_number', 'volume', 'isbn_10', 'isbn_13', 
                      'classification_number', 'cutter_number', 'call_number'),
            'description': 'Accession number must be unique. Call number is auto-generated.'
        }),
        ('Content Details', {
            'fields': ('category', 'language', 'pages', 'edition', 
                      'description', 'description_bangla', 'keywords', 'keywords_bangla')
        }),
        ('Physical & Location', {
            'fields': ('total_copies', 'copies_available', 'location_shelf', 'cover_image')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'price', 'times_borrowed'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['call_number', 'times_borrowed', 'created_at', 'updated_at']
    
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('upload-csv/', self.admin_site.admin_view(self.upload_csv), name='library_book_upload_csv'),
        ]
        return my_urls + urls

    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                self.message_user(request, "No file uploaded.", level=messages.ERROR)
                return redirect(".")
            if not csv_file.name.endswith('.csv'):
                self.message_user(request, "This is not a csv file.", level=messages.ERROR)
                return redirect(".")

            fs = FileSystemStorage(location='media/library/csv_uploads')
            filename = fs.save(csv_file.name, csv_file)
            file_path = fs.path(filename)

            try:
                call_command('import_books', file_path)
                self.message_user(request, "Successfully imported books from CSV file.")
            except CommandError as e:
                self.message_user(request, f"Error importing books: {e}", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, f"An unexpected error occurred: {e}", level=messages.ERROR)

            return redirect("..")
        
        context = self.admin_site.each_context(request)
        return render(request, "admin/library/book/upload_csv.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['download_csv_template_url'] = reverse('library:download_csv_template')
        extra_context['upload_csv_url'] = reverse('admin:library_book_upload_csv')
        from django.template.loader import render_to_string
        from django.utils.safestring import mark_safe
        instructions = render_to_string('admin/library/book/import_instructions.html', request=request)
        extra_context['import_instructions'] = mark_safe(
            f'<div id="import-instructions-container" style="display: none;">{instructions}</div>'
            '<script>'
            'document.addEventListener("DOMContentLoaded", function() {'
            '    const instructions = document.getElementById("import-instructions-container");'
            '    const content = document.getElementById("content-main");'
            '    if (instructions && content) {'
            '        content.insertAdjacentHTML("afterbegin", instructions.innerHTML);'
            '    }'
            '});'
            '</script>'
        )
        return super().changelist_view(request, extra_context=extra_context)

    def authors_display(self, obj):
        authors = obj.authors.all()
        if authors:
            return ", ".join([author.full_name for author in authors[:2]])
        return "No authors"
    authors_display.short_description = 'Authors'
    
    def availability_status(self, obj):
        if obj.is_available:
            color = 'green'
            text = f'Available ({obj.copies_available}/{obj.total_copies})'
        else:
            color = 'red'
            text = f'Not Available ({obj.copies_available}/{obj.total_copies})'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    availability_status.short_description = 'Availability'
    
    actions = ['mark_as_available', 'mark_as_checked_out', 'mark_as_damaged']
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(status='available')
        self.message_user(request, f'{updated} books marked as available.')
    mark_as_available.short_description = "Mark selected books as available"
    
    def mark_as_checked_out(self, request, queryset):
        updated = queryset.update(status='checked_out')
        self.message_user(request, f'{updated} books marked as checked out.')
    mark_as_checked_out.short_description = "Mark selected books as checked out"
    
    def mark_as_damaged(self, request, queryset):
        updated = queryset.update(status='damaged')
        self.message_user(request, f'{updated} books marked as damaged.')
    mark_as_damaged.short_description = "Mark selected books as damaged"

@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = [
        'borrower_name', 'book_title', 'borrow_date', 'due_date', 
        'status_badge', 'fine_display', 'renewal_info', 'actions_column'
    ]
    list_filter = [
        'status', 'borrow_date', 'due_date', 'fine_paid', 'renewal_count'
    ]
    search_fields = [
        'borrower__username', 'borrower__email', 'borrower__first_name', 
        'borrower__last_name'
    ]
    readonly_fields = [
        'borrow_date', 'created_at', 'updated_at', 'first_reminder_sent',
        'second_reminder_sent', 'overdue_reminder_sent'
    ]
    
    fieldsets = (
        ('Borrowing Information', {
            'fields': (('content_type', 'object_id'), 'borrower', 'borrow_date', 'due_date', 'return_date')
        }),
        ('Status & Fines', {
            'fields': ('status', 'fine_amount', 'fine_paid')
        }),
        ('Renewal Information', {
            'fields': ('renewal_count',)
        }),
        ('Email Tracking', {
            'fields': ('first_reminder_sent', 'second_reminder_sent', 'overdue_reminder_sent'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'borrow_date'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:record_id>/renew/', self.admin_site.admin_view(self.renew_book), name='library_borrowrecord_renew'),
            path('<int:record_id>/return/', self.admin_site.admin_view(self.return_book), name='library_borrowrecord_return'),
            path('<int:record_id>/send-reminder/', self.admin_site.admin_view(self.send_reminder), name='library_borrowrecord_reminder'),
            path('<int:record_id>/mark-as-paid/', self.admin_site.admin_view(self.mark_as_paid), name='library_borrowrecord_mark_as_paid'),
            path('<int:record_id>/undo-return/', self.admin_site.admin_view(self.undo_return), name='library_borrowrecord_undo_return'),
        ]
        return custom_urls + urls
    
    def borrower_name(self, obj):
        return obj.borrower.get_full_name() or obj.borrower.username
    borrower_name.short_description = 'Borrower'
    borrower_name.admin_order_field = 'borrower__last_name'
    
    def book_title(self, obj):
        publication = obj.publication
        if not publication:
            return "N/A"
        volume_str = ""
        if hasattr(publication, 'volume') and publication.volume:
            volume_str = f" ({publication.volume})"
        return f"{publication.title}{volume_str}"
    book_title.short_description = 'Publication'
    
    def status_badge(self, obj):
        colors = {
            'active': '#10B981',
            'returned': '#6B7280',
            'overdue': '#EF4444',
            'lost': '#F59E0B',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6B7280'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def fine_display(self, obj):
        if obj.fine_amount > 0:
            paid_status = '✓ Paid' if obj.fine_paid else '✗ Unpaid'
            color = 'green' if obj.fine_paid else 'red'
            return format_html(
                '৳{:.2f} <span style="color: {};">{}</span>',
                obj.fine_amount, color, paid_status
            )
        return '-'
    fine_display.short_description = 'Fine'
    
    def renewal_info(self, obj):
        if obj.status == 'active':
            setting = LibrarySetting.objects.first()
            max_renewals = setting.max_renewals if setting else 2
            return f"{obj.renewal_count}/{max_renewals} renewals"
        return '-'
    renewal_info.short_description = 'Renewals'
    
    def actions_column(self, obj):
        buttons = []
        if obj.status == 'active':
            if obj.can_renew:
                renew_url = reverse('admin:library_borrowrecord_renew', args=[obj.id])
                buttons.append(
                    f'<a class="button" href="{renew_url}" style="background-color: #3B82F6; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; margin-right: 5px;">Renew</a>'
                )
            
            return_url = reverse('admin:library_borrowrecord_return', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{return_url}" style="background-color: #10B981; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; margin-right: 5px;">Return</a>'
            )
        elif obj.status == 'overdue' and not obj.fine_paid:
            mark_as_paid_url = reverse('admin:library_borrowrecord_mark_as_paid', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{mark_as_paid_url}" style="background-color: #10B981; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Mark as Paid</a>'
            )

        reminder_url = reverse('admin:library_borrowrecord_reminder', args=[obj.id])
        buttons.append(
            f'<a class="button" href="{reminder_url}" style="background-color: #F59E0B; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">Send Reminder</a>'
        )

        if obj.status == 'returned' and obj.return_date and (timezone.now() - obj.return_date).days < 1:
            undo_return_url = reverse('admin:library_borrowrecord_undo_return', args=[obj.id])
            buttons.append(
                f'<a class="button" href="{undo_return_url}" style="background-color: #78716c; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; margin-left: 5px;">Undo Return</a>'
            )
        
        return format_html(''.join(buttons))
    actions_column.short_description = 'Actions'


    def changelist_view(self, request, extra_context=None):
        """Add summary statistics to changelist"""
        extra_context = extra_context or {}
        
        # Get statistics
        active_count = BorrowRecord.objects.filter(status='active').count()
        overdue_count = BorrowRecord.objects.filter(status='overdue').count()
        total_fines = BorrowRecord.objects.filter(
            fine_amount__gt=0, 
            fine_paid=False
        ).aggregate(Sum('fine_amount'))['fine_amount__sum'] or 0
        
        extra_context['stats'] = {
            'active_count': active_count,
            'overdue_count': overdue_count,
            'total_unpaid_fines': total_fines,
        }
        
        return super().changelist_view(request, extra_context=extra_context)
    
    def send_bulk_reminders(self, request, queryset):
        """Send reminder emails to selected borrowers"""
        sent_count = 0
        error_count = 0
        
        for record in queryset.filter(status__in=['active', 'overdue']):
            try:
                if record.status == 'overdue':
                    LibraryEmailService.send_overdue_notice(record)
                elif record.days_until_due <= 3:
                    LibraryEmailService.send_first_reminder(record)
                sent_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to send reminder for record {record.id}: {str(e)}")
        
        if sent_count > 0:
            self.message_user(
                request,
                f'Successfully sent {sent_count} reminder emails.',
                messages.SUCCESS
            )
        if error_count > 0:
            self.message_user(
                request,
                f'Failed to send {error_count} emails.',
                messages.WARNING
            )
    
    send_bulk_reminders.short_description = "Send reminder emails to selected borrowers"
    
    actions = ['mark_as_returned', 'send_reminders_action', 'calculate_fines', 'send_bulk_reminders']
    
    def renew_book(self, request, record_id):
        record = get_object_or_404(BorrowRecord, id=record_id)
        
        try:
            record.renew()
            LibraryEmailService.send_renewal_confirmation(record)
            messages.success(request, f'Book renewed successfully. New due date: {record.due_date}')
        except ValueError as e:
            messages.error(request, str(e))
        
        return HttpResponseRedirect(reverse('admin:library_borrowrecord_changelist'))
    
    def return_book(self, request, record_id):
        record = get_object_or_404(BorrowRecord, id=record_id)
        
        if record.status in ['returned', 'lost']:
            messages.warning(request, 'This book has already been returned or marked as lost.')
        else:
            record.return_book()
            LibraryEmailService.send_return_confirmation(record)
            messages.success(request, f'Book returned successfully.')
        
        return HttpResponseRedirect(reverse('admin:library_borrowrecord_changelist'))
    
    def send_reminder(self, request, record_id):
        record = get_object_or_404(BorrowRecord, id=record_id)
        
        if record.status == 'active':
            days_until_due = record.days_until_due
            
            if days_until_due >= 2:
                LibraryEmailService.send_first_reminder(record)
                messages.success(request, f'Reminder email sent to {record.borrower.email}')
            elif days_until_due == 1:
                LibraryEmailService.send_second_reminder(record)
                messages.success(request, f'Urgent reminder email sent to {record.borrower.email}')
            else:
                LibraryEmailService.send_overdue_notice(record)
                messages.success(request, f'Overdue notice sent to {record.borrower.email}')
        else:
            messages.warning(request, 'Cannot send reminder for non-active borrow records.')
        
        return HttpResponseRedirect(reverse('admin:library_borrowrecord_changelist'))

    def mark_as_paid(self, request, record_id):
        record = get_object_or_404(BorrowRecord, id=record_id)
        record.fine_paid = True
        record.save()
        messages.success(request, f'Fine for "{record.publication.title}" marked as paid.')
        return HttpResponseRedirect(reverse('admin:library_borrowrecord_changelist'))

    def undo_return(self, request, record_id):
        record = get_object_or_404(BorrowRecord, id=record_id)
        try:
            record.undo_return()
            messages.success(request, f'Return of "{record.publication.title}" has been undone.')
        except ValueError as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(reverse('admin:library_borrowrecord_changelist'))
    
    actions = ['mark_as_returned', 'send_reminders_action', 'calculate_fines']
    
    def mark_as_returned(self, request, queryset):
        count = 0
        for record in queryset:
            if record.status == 'active' or record.status == 'overdue':
                record.return_book()
                LibraryEmailService.send_return_confirmation(record)
                count += 1
        
        self.message_user(request, f'{count} books marked as returned.')
    mark_as_returned.short_description = "Mark selected as returned"
    
    def send_reminders_action(self, request, queryset):
        count = 0
        for record in queryset.filter(status='active'):
            if record.days_until_due <= 3:
                LibraryEmailService.send_first_reminder(record)
                count += 1
        
        self.message_user(request, f'Sent reminders for {count} borrow records.')
    send_reminders_action.short_description = "Send reminder emails"
    
    def calculate_fines(self, request, queryset):
        count = 0
        for record in queryset:
            if record.is_overdue:
                days_overdue = (timezone.now().date() - record.due_date).days
                record.fine_amount = days_overdue * 5.00
                record.status = 'overdue'
                record.save()
                count += 1
        
        self.message_user(request, f'Calculated fines for {count} overdue books.')
    calculate_fines.short_description = "Calculate fines for overdue books"

@admin.register(BookSearch)
class BookSearchAdmin(admin.ModelAdmin):
    list_display = ['query', 'language_detected', 'search_count', 'last_searched']
    list_filter = ['language_detected', 'last_searched']
    search_fields = ['query']
    readonly_fields = ['query', 'language_detected', 'search_count', 'last_searched']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(LibrarySetting)
class LibrarySettingAdmin(admin.ModelAdmin):
    """Admin interface for library settings"""
    list_display = ('overdue_fine_per_day', 'loan_period', 'renewal_period', 'max_renewals', 'max_books_per_user')
    
    def has_add_permission(self, request):
        # Prevents adding new settings from the admin
        return not LibrarySetting.objects.exists()