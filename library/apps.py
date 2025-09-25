# library/apps.py

from django.apps import AppConfig

class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'
    verbose_name = 'Library Management'
    
    def ready(self):
        # Import any signal handlers here if needed
        pass