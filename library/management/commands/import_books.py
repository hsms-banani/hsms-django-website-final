import csv
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from library.models import Book, Author, Category, Publisher

class Command(BaseCommand):
    help = 'Imports books from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the CSV file to import')

    def handle(self, *args, **options):
        file_path = options['file_path']
        created_count = 0
        updated_count = 0
        skipped_count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    try:
                        # Get or create Category
                        category_name = row.get('category*', '').strip()
                        if not category_name:
                            self.stdout.write(self.style.WARNING(f"Skipping row due to missing category: {row.get('title*')}"))
                            skipped_count += 1
                            continue
                        category, _ = Category.objects.get_or_create(
                            name=category_name,
                            defaults={'slug': slugify(category_name)}
                        )

                        # Get or create Publisher
                        publisher_name = row.get('publisher*', '').strip()
                        if not publisher_name:
                            self.stdout.write(self.style.WARNING(f"Skipping row due to missing publisher: {row.get('title*')}"))
                            skipped_count += 1
                            continue
                        publisher, _ = Publisher.objects.get_or_create(
                            name=publisher_name,
                            defaults={'slug': slugify(publisher_name)}
                        )

                        # Prepare book data
                        book_data = {
                            'title': row.get('title*', '').strip(),
                            'subtitle': row.get('subtitle', '').strip(),
                            'publication_year': int(row.get('publication_year*', 0)),
                            'description': row.get('description', '').strip(),
                            'category': category,
                            'publisher': publisher,
                            'isbn_10': row.get('isbn_10', '').strip(),
                            'isbn_13': row.get('isbn_13', '').strip(),
                            'classification_number': row.get('classification_number*', '').strip(),
                            'cutter_number': row.get('cutter_number*', '').strip(),
                            'language': row.get('language', 'en').strip(),
                            'pages': int(row.get('pages', 0)),
                            'edition': row.get('edition', '').strip(),
                            'keywords': row.get('keywords', '').strip(),
                            'total_copies': int(row.get('total_copies', 1)),
                            'copies_available': int(row.get('copies_available', 1)),
                            'location_shelf': row.get('location_shelf', '').strip(),
                            'status': row.get('status', 'available').strip(),
                        }

                        # Create or update Book
                        book, created = Book.objects.update_or_create(
                            isbn_13=book_data['isbn_13'],
                            defaults=book_data
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                        # Add Authors
                        author_names = row.get('author*', '').strip().split(';')
                        book.authors.clear()
                        for name in author_names:
                            name = name.strip()
                            if not name:
                                continue
                            
                            parts = name.split()
                            first_name = parts[0]
                            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
                            
                            author, _ = Author.objects.get_or_create(
                                first_name=first_name,
                                last_name=last_name,
                                defaults={'slug': slugify(name)}
                            )
                            book.authors.add(author)

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error processing row for book '{row.get('title*')}': {e}"))
                        skipped_count += 1
                        continue

        except FileNotFoundError:
            raise CommandError(f'File not found at: {file_path}')
        except Exception as e:
            raise CommandError(f'An error occurred: {e}')

        self.stdout.write(self.style.SUCCESS(f'Finished importing books.'))
        self.stdout.write(f'Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}')
