# students/views.py 
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import models # <--- Added this line
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from .models import (
    Student
)
from .serializers import (
    StudentSerializer
)

@method_decorator(csrf_exempt, name='dispatch')
class StudentList(generics.ListAPIView):
    serializer_class = StudentSerializer
    
    def get_queryset(self):
        # Get filters
        search_name = self.request.query_params.get('search_name', None) or self.request.query_params.get('name', None) or self.request.query_params.get('search', None)
        status = self.request.query_params.get('status', 'active')
        student_type = self.request.query_params.get('student_type', None)
        affiliation = self.request.query_params.get('affiliation', None)
        year_joined = self.request.query_params.get('year_joined', None)
        name_of_study = self.request.query_params.get('name_of_study', None)
        year_completed = self.request.query_params.get('year_completed', None)
        
        queryset = Student.objects.all()

        # Apply search by student name filter
        if search_name and search_name.strip():
            query = search_name.strip()
            queryset = queryset.filter(
                models.Q(name__icontains=query) | models.Q(student_id__icontains=query)
            )

        # Apply status filter
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        # Apply student type filter
        if student_type:
            queryset = queryset.filter(student_type=student_type)
        
        # Apply affiliation filter (searches in diocese or congregation based on student_type, or both if student_type is not specified)
        if affiliation and affiliation.strip():
            aff = affiliation.strip()
            if student_type == 'diocesan':
                queryset = queryset.filter(diocese__icontains=aff)
            elif student_type == 'congregation':
                queryset = queryset.filter(congregation__icontains=aff)
            else: # Search in both if student_type is not specified
                queryset = queryset.filter(models.Q(diocese__icontains=aff) | models.Q(congregation__icontains=aff))
        
        # Apply year joined filter
        if year_joined:
            queryset = queryset.filter(year_joined=year_joined)
            
        # Apply name of study filter
        if name_of_study and name_of_study.strip():
            queryset = queryset.filter(name_of_study__icontains=name_of_study.strip())
            
        # Apply year completed filter
        if year_completed:
            queryset = queryset.filter(year_completed=year_completed)
        
        return queryset.order_by('name')

@method_decorator(csrf_exempt, name='dispatch')
class CongregationList(generics.ListAPIView):
    serializer_class = StudentSerializer
    
    def get_queryset(self):
        status = self.request.query_params.get('status', 'active')
        if status == 'all':
            return Student.objects.all()
        else:
            return Student.objects.filter(status=status)
    
    def list(self, request, *args, **kwargs):
        status = self.request.query_params.get('status', 'active')
        
        # Build base queryset
        if status == 'all':
            base_queryset = Student.objects.all()
        else:
            base_queryset = Student.objects.filter(status=status)
        
        # Get congregation and diocese statistics
        congregations = base_queryset.values('congregation').annotate(
            count=Count('id')
        ).order_by('congregation')
        
        dioceses = base_queryset.values('diocese').annotate(
            count=Count('id')
        ).order_by('diocese')
        
        return Response({
            'congregations': list(congregations),
            'dioceses': list(dioceses),
            'total_students': base_queryset.count(),
            'status_filter': status
        })

