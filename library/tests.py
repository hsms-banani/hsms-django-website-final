from django.test import TestCase
from django.contrib.auth.models import User
from .utils import process_bulk_user_csv
from io import StringIO
from django.core.files.uploadedfile import SimpleUploadedFile

class BulkUserUploadTest(TestCase):

    def test_bulk_user_upload_success(self):
        """Test bulk user upload with a valid CSV file."""
        csv_data = (
            'first_name*,last_name*,email*,username\n'
            'John,Doe,john.doe@example.com,johndoe\n'
            'Jane,Smith,jane.smith@example.com,janesmith\n'
        )
        csv_file = SimpleUploadedFile("users.csv", csv_data.encode('utf-8'), content_type="text/csv")

        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

        result = process_bulk_user_csv(csv_file, admin_user)

        self.assertEqual(result['successful_imports'], 2)
        self.assertEqual(result['failed_imports'], 0)
        self.assertEqual(User.objects.count(), 3)  # admin + 2 new users

    def test_bulk_user_upload_invalid_data(self):
        """Test bulk user upload with an invalid CSV file."""
        csv_data = (
            'first_name*,last_name*,email*,username\n'
            'Lawrence,Palm,palma@gmail.com,\n'
            ',MacField,prince@gmail.com,\n'
            'Racy,Daniel,,\n'
        )
        csv_file = SimpleUploadedFile("users.csv", csv_data.encode('utf-8'), content_type="text/csv")

        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

        result = process_bulk_user_csv(csv_file, admin_user)

        self.assertEqual(result['successful_imports'], 1)
        self.assertEqual(result['failed_imports'], 2)
        self.assertEqual(User.objects.count(), 2)  # admin + 1 new user
