
# utils/views.py
import csv
import io
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from students.models import Student
from .forms import CsvImportForm

@login_required
def download_student_csv_template(request):
    """
    A view to download a CSV template for importing students.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_import_template.csv"'

    writer = csv.writer(response)
    writer.writerow(['name', 'student_type', 'diocese', 'congregation', 'year_joined', 'name_of_study', 'year_completed', 'student_id', 'email', 'phone', 'status'])
    writer.writerow(['Sample Student', 'diocesan', 'Sample Diocese', '', '2023', 'Philosophy', '', 'S001', 'sample@example.com', '1234567890', 'active'])
    writer.writerow(['Another Student', 'congregation', '', 'Sample Congregation', '2022', 'Theology', '2025', 'S002', 'another@example.com', '0987654321', 'graduated'])

    return response

@login_required
def import_students_from_csv(request):
    if request.method == "POST":
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["csv_file"]
            
            # Check if the file is a CSV file
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'This is not a CSV file. Please upload a valid CSV file.')
                return redirect(request.path)

            try:
                # Decode the file
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                
                # Use DictReader to read the CSV
                reader = csv.DictReader(io_string)
                
                # Required columns
                required_columns = ['name', 'student_type', 'year_joined']
                
                # Check for required columns in the header
                if not all(col in reader.fieldnames for col in required_columns):
                    missing_cols = [col for col in required_columns if col not in reader.fieldnames]
                    messages.error(request, f"The CSV file is missing the following required columns: {', '.join(missing_cols)}")
                    return redirect(request.path)

                students_to_create = []
                errors = []

                for i, row in enumerate(reader, start=2): # Start from row 2 for error reporting
                    # Basic validation
                    if not row.get('name') or not row.get('student_type') or not row.get('year_joined'):
                        errors.append(f"Row {i}: Missing required data. 'name', 'student_type', and 'year_joined' are required.")
                        continue

                    if row['student_type'] not in ['diocesan', 'congregation']:
                        errors.append(f"Row {i}: Invalid 'student_type'. It must be either 'diocesan' or 'congregation'.")
                        continue
                        
                    if row['student_type'] == 'diocesan' and not row.get('diocese'):
                        errors.append(f"Row {i}: 'diocese' is required for students of type 'diocesan'.")
                        continue

                    if row['student_type'] == 'congregation' and not row.get('congregation'):
                        errors.append(f"Row {i}: 'congregation' is required for students of type 'congregation'.")
                        continue

                    students_to_create.append(Student(
                        name=row['name'],
                        student_type=row['student_type'],
                        diocese=row.get('diocese', ''),
                        congregation=row.get('congregation', ''),
                        year_joined=row['year_joined'],
                        name_of_study=row.get('name_of_study', ''),
                        year_completed=row.get('year_completed', ''),
                        student_id=row.get('student_id', ''),
                        email=row.get('email', ''),
                        phone=row.get('phone', ''),
                        status=row.get('status', 'active'),
                    ))

                if errors:
                    for error in errors:
                        messages.error(request, error)
                else:
                    Student.objects.bulk_create(students_to_create)
                    messages.success(request, f"Successfully imported {len(students_to_create)} students.")
                    return redirect(reverse('admin:students_student_changelist'))

            except Exception as e:
                messages.error(request, f"An error occurred while processing the file: {e}")
        else:
            for field, error_list in form.errors.items():
                for error in error_list:
                    messages.error(request, f"Form error in {field}: {error}")

    form = CsvImportForm()
    context = {
        'form': form,
        'opts': Student._meta,
        'site_header': 'Holy Spirit Major Seminary Admin',
        'title': 'Import Students from CSV',
        'csv_instructions': {
            'headers': ['name', 'student_type', 'diocese', 'congregation', 'year_joined', 'name_of_study', 'year_completed', 'student_id', 'email', 'phone', 'status'],
            'required': ['name', 'student_type', 'year_joined'],
            'student_type': "Must be either 'diocesan' or 'congregation'.",
            'conditional_required': {
                'diocesan': "If student_type is 'diocesan', 'diocese' is required.",
                'congregation': "If student_type is 'congregation', 'congregation' is required."
            },
            'optional': ['name_of_study', 'year_completed', 'student_id', 'email', 'phone', 'status'],
            'status': "Defaults to 'active' if not provided. Choices are: active, graduated, transferred, suspended."
        }
    }
    return render(request, "admin/csv_import.html", context)
