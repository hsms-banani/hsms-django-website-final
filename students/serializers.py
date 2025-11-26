# students/serializers.py
from rest_framework import serializers
from .models import (
    Student
)

class StudentSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'student_type', 'congregation', 'diocese', 'year_joined', 'name_of_study', 'year_completed',
            'student_id', 'email', 'phone', 'photo', 'photo_url', 'status'
        ]
    
    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

