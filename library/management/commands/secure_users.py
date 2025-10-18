# library/management/commands/secure_users.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Ensures that only superusers have the is_staff flag set to True.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Running security check for user permissions...'))

        users_updated = 0
        for user in User.objects.all():
            if not user.is_superuser and user.is_staff:
                user.is_staff = False
                user.save()
                users_updated += 1
                self.stdout.write(self.style.WARNING(f'User "{user.username}" is no longer a staff member.'))

        if users_updated > 0:
            self.stdout.write(self.style.SUCCESS(f'Security check complete. {users_updated} users were updated.'))
        else:
            self.stdout.write(self.style.SUCCESS('Security check complete. All users are correctly configured.'))
