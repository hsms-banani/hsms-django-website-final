
# utils/urls.py
from django.urls import path
from . import views

app_name = 'utils'

urlpatterns = [
    path('import-students/', views.import_students_from_csv, name='import_students'),
]
