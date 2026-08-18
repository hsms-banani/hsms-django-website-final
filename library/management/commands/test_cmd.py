from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--task-id', type=int)
    def handle(self, *args, **options):
        print("TASK ID IS:", options.get('task_id'))
