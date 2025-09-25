# library/admin.py

from django.contrib import admin, messages
from django.utils.html import format_html
from django.db.models import Count
from .models import Category, Publisher, Author, Book, BookSearch
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'book_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = 'Books'

@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'website', 'established_year', 'book_count', 'created_at']
    list_filter = ['established_year', 'created_at']
    search_fields = ['name', 'address']
    prepopulated_fields = {'slug': ('name',)}
    
    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = 'Books Published'

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'nationality', 'birth_year', 'death_year', 'book_count']
    list_filter = ['nationality', 'birth_year']
    search_fields = ['first_name', 'last_name', 'bio']
    prepopulated_fields = {'slug': ('first_name', 'last_name')}
    
    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = 'Books Written'

class BookAuthorInline(admin.TabularInline):
    model = Book.authors.through
    extra = 1

from django.urls import path, reverse
from django.shortcuts import render, redirect

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'authors_display', 'publisher', 'publication_year', 
        'call_number', 'category', 'availability_status', 'times_borrowed'
    ]
    list_filter = [
        'status', 'category', 'language', 'publication_year', 
        'publisher', 'acquisition_date'
    ]
    search_fields = [
        'title', 'subtitle', 'isbn_10', 'isbn_13', 'call_number',
        'classification_number', 'cutter_number', 'keywords',
        'authors__first_name', 'authors__last_name'
    ]
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['authors']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subtitle', 'slug', 'authors', 'publisher', 'publication_year')
        }),
        ('Classification', {
            'fields': ('isbn_10', 'isbn_13', 'classification_number', 'cutter_number', 'call_number'),
            'description': 'Call number is auto-generated from classification + cutter number'
        }),
        ('Content Details', {
            'fields': ('category', 'language', 'pages', 'edition', 'description', 'keywords')
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

            # Save the uploaded file to a temporary location
            fs = FileSystemStorage(location='media/library/csv_uploads')
            filename = fs.save(csv_file.name, csv_file)
            file_path = fs.path(filename)

            try:
                call_command('import_books', file_path)
                self.message_user(request, "Successfully imported books from CSV file.")
            except Exception as e:
                self.message_user(request, f"Error importing books: {e}", level=messages.ERROR)

            return redirect("..")
        
        context = self.admin_site.each_context(request)
        return render(request, "admin/library/book/upload_csv.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['download_csv_template_url'] = reverse('library:download_csv_template')
        extra_context['upload_csv_url'] = reverse('admin:library_book_upload_csv')
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

@admin.register(BookSearch)
class BookSearchAdmin(admin.ModelAdmin):
    list_display = ['query', 'search_count', 'last_searched']
    list_filter = ['last_searched']
    search_fields = ['query']
    readonly_fields = ['query', 'search_count', 'last_searched']
    
    def has_add_permission(self, request):
        return False  # Prevent manual addition
    
    def has_change_permission(self, request, obj=None):
        return False  # Prevent editing
