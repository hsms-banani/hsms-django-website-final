import random
from django.core.management.base import BaseCommand
from library.models import Author, Publisher, Category, Book

class Command(BaseCommand):
    help = 'Populates the library with dummy data'

    def add_arguments(self, parser):
        parser.add_argument('--books', type=int, help='Number of books to create', default=100)
        parser.add_argument('--authors', type=int, help='Number of authors to create', default=50)
        parser.add_argument('--publishers', type=int, help='Number of publishers to create', default=20)
        parser.add_argument('--categories', type=int, help='Number of categories to create', default=10)

    def handle(self, *args, **options):
        num_books = options['books']
        num_authors = options['authors']
        num_publishers = options['publishers']
        num_categories = options['categories']

        self.stdout.write('Creating dummy data...')

        # Create Categories
        categories = []
        for i in range(num_categories):
            category, created = Category.objects.get_or_create(name=f'Category {i}')
            categories.append(category)

        # Create Publishers
        publishers = []
        for i in range(num_publishers):
            publisher, created = Publisher.objects.get_or_create(name=f'Publisher {i}')
            publishers.append(publisher)

        # Create Authors
        authors = []
        for i in range(num_authors):
            author, created = Author.objects.get_or_create(
                first_name=f'Author {i}',
                last_name='Lastname'
            )
            authors.append(author)

        # Create Books
        for i in range(num_books):
            book = Book.objects.create(
                title=f'Book Title {i}',
                publisher=random.choice(publishers),
                category=random.choice(categories),
                publication_year=random.randint(1980, 2025),
                classification_number=f'{random.randint(100, 999)}.{random.randint(1, 9)}',
                cutter_number=f'A{random.randint(10, 99)}',
                total_copies=random.randint(1, 5),
                copies_available=random.randint(0, 5),
            )
            book.authors.set(random.sample(authors, k=random.randint(1, 3)))

        self.stdout.write(self.style.SUCCESS('Successfully populated the library with dummy data.'))