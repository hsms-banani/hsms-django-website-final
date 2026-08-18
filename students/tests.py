# students/tests.py
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Student

class StudentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student1 = Student.objects.create(
            name="Aiyub Augustine Ghagra",
            student_id="STU001",
            student_type="diocesan",
            diocese="Mymensingh",
            year_joined="2022",
            name_of_study="Theology",
            status="active"
        )
        self.student2 = Student.objects.create(
            name="Anjan Francis Sikder",
            student_id="STU002",
            student_type="diocesan",
            diocese="Barishal",
            year_joined="2019",
            year_completed="2026",
            name_of_study="Theology",
            status="active"
        )
        self.student3 = Student.objects.create(
            name="Apurba Anthony Hajong",
            student_id="STU003",
            student_type="congregation",
            congregation="Congregatio a Sancta Cruce",
            year_joined="2020",
            name_of_study="Theology",
            status="graduated"
        )

    def test_student_list_all(self):
        response = self.client.get('/api/students/list/?status=all')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_search_by_name(self):
        # Search by partial name
        response = self.client.get('/api/students/list/?status=all&search_name=Augustine')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Aiyub Augustine Ghagra")

        # Search by student_id
        response = self.client.get('/api/students/list/?status=all&name=STU002')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Anjan Francis Sikder")

    def test_search_by_name_and_status(self):
        # Active status with search
        response = self.client.get('/api/students/list/?status=active&search_name=Anthony')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # Graduated status with search
        response = self.client.get('/api/students/list/?status=graduated&search_name=Anthony')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
