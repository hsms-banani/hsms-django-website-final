# students/api_urls.py 
from django.urls import path
from .views import (
    StudentList,
    CongregationList
)

app_name = 'students_api'

urlpatterns = [
    path('list/', StudentList.as_view(), name='student-list'),
    path('congregations/', CongregationList.as_view(), name='congregations'),
]