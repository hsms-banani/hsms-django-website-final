# students/admin.py
from django.contrib import admin
from django.urls import path
from utils.views import import_students_from_csv, download_student_csv_template
from .models import (
    Student
)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    change_list_template = "admin/students/student/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.admin_site.admin_view(import_students_from_csv), name='import_students_csv'),
            path('download-template/', self.admin_site.admin_view(download_student_csv_template), name='download_student_csv_template'),
        ]
        return my_urls + urls
        
    list_display = ['name', 'student_type', 'affiliation', 'year_joined', 'name_of_study', 'year_completed', 'status']
    list_filter = ['status', 'student_type', 'year_joined', 'year_completed', 'name_of_study']
    search_fields = ['name', 'student_id', 'email', 'congregation', 'diocese', 'name_of_study']
    list_editable = ['status']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'student_id', 'photo')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Academic Information', {
            'fields': ('student_type', 'diocese', 'congregation', 'year_joined', 'name_of_study', 'year_completed', 'status')
        }),
    )

    def affiliation(self, obj):
        if obj.student_type == 'diocesan':
            return obj.diocese
        elif obj.student_type == 'congregation':
            return obj.congregation
        return '-'
    affiliation.short_description = 'Affiliation'

    class Media:
        js = ('admin/js/student_admin.js',)

