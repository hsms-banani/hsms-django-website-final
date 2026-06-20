# students/models.py
from django.db import models
from django.core.validators import FileExtensionValidator
from utils.image_optimizer import optimize_image
class Student(models.Model):
    STUDENT_TYPE_CHOICES = [
        ('diocesan', 'Diocesan'),
        ('congregation', 'Congregation'),
    ]
    name = models.CharField(max_length=200)
    student_type = models.CharField(max_length=20, choices=STUDENT_TYPE_CHOICES, default='diocesan')
    congregation = models.CharField(max_length=200, blank=True)
    diocese = models.CharField(max_length=200, blank=True)
    year_joined = models.CharField(max_length=4)
    name_of_study = models.CharField(max_length=200, blank=True)
    year_completed = models.CharField(max_length=4, blank=True)
    student_id = models.CharField(max_length=50, unique=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('graduated', 'Graduated'),
        ('transferred', 'Transferred'),
        ('suspended', 'Suspended')
    ], default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Prevent recursive saving
        if self.photo and not getattr(self, '_photo_optimized', False):
            optimized = optimize_image(self.photo, max_width=800, max_height=800)
            if optimized:
                self.photo = optimized
            self._photo_optimized = True
        super().save(*args, **kwargs)
