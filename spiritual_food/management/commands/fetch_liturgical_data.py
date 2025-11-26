# spiritual_food/management/commands/fetch_liturgical_data.py
import requests
from django.core.management.base import BaseCommand
from spiritual_food.models import LiturgicalCalendar, Saint
from datetime import datetime

class Command(BaseCommand):
    help = 'Fetches liturgical data from the calapi.inadiutorium.cz API and populates the database.'

    def add_arguments(self, parser):
        parser.add_argument('year', type=int, help='The year to fetch data for.')

    def handle(self, *args, **options):
        year = options['year']
        url = f'http://calapi.inadiutorium.cz/api/v0/en/calendars/general-roman/{year}'

        self.stdout.write(f'Fetching data for {year} from {url}...')
        
        try:
            response = response = requests.get(url, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Error fetching data: {e}'))
            return

        self.stdout.write('Data fetched successfully. Populating database...')

        for celebration in data:
            date_str = celebration.get('date')
            if not date_str:
                continue

            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.WARNING(f"Skipping celebration due to invalid date format: {date_str}"))
                continue

            liturgical_day, created = LiturgicalCalendar.objects.get_or_create(date=date)

            liturgical_day.name = celebration.get('title', '')
            liturgical_day.season = celebration.get('season', '').lower()
            liturgical_day.rank = celebration.get('rank', 'weekday')
            liturgical_day.color = celebration.get('color', 'green')
            
            # Readings are not directly available in this API response, so we leave them blank
            # The user can manually add them if needed
            
            # The API does not provide cycle information, this would need to be calculated
            # or entered manually. For simplicity, we are leaving it blank.

            # Create or get saints and add them to the liturgical day
            if 'saints' in celebration:
                for saint_data in celebration['saints']:
                    saint, _ = Saint.objects.get_or_create(name=saint_data['name'])
                    liturgical_day.saints.add(saint)
            
            liturgical_day.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully populated liturgical calendar for {year}.'))
