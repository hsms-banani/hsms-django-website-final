# library/management/commands/import_books.py
"""
Management command to import books from CSV files with full Unicode support
Supports accession_number and volume fields
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from library.models import Book, Author, Category, Publisher
from library.utils import normalize_unicode_text, create_multilingual_slug
import csv
import chardet
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import books from a CSV file with Unicode support'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--encoding',
            type=str,
            default=None,
            help='Specify CSV encoding (auto-detected if not provided)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving to database'
        )

    def detect_encoding(self, file_path):
        """Auto-detect file encoding"""
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result['encoding']

    def get_or_create_authors(self, author_string):
        """Parse and create/get authors from semicolon-separated string"""
        if not author_string:
            return []
        
        authors = []
        author_names = [name.strip() for name in author_string.split(';') if name.strip()]
        
        for name in author_names:
            # Try to split into first and last name
            parts = name.rsplit(' ', 1)
            if len(parts) == 2:
                first_name, last_name = parts
            else:
                first_name = name
                last_name = ''
            
            # Normalize names
            first_name = normalize_unicode_text(first_name)
            last_name = normalize_unicode_text(last_name)
            
            # Create or get author
            author, created = Author.objects.get_or_create(
                first_name=first_name,
                last_name=last_name,
                defaults={
                    'slug': create_multilingual_slug(f"{first_name} {last_name}")
                }
            )
            authors.append(author)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created author: {author.full_name}'))
        
        return authors

    def get_or_create_category(self, category_name):
        """Get or create category"""
        if not category_name:
            raise ValueError("Category is required")
        
        category_name = normalize_unicode_text(category_name)
        category, created = Category.objects.get_or_create(
            name=category_name,
            defaults={'slug': create_multilingual_slug(category_name)}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created category: {category.name}'))
        
        return category

    def get_or_create_publisher(self, publisher_name):
        """Get or create publisher"""
        if not publisher_name:
            raise ValueError("Publisher is required")
        
        publisher_name = normalize_unicode_text(publisher_name)
        publisher, created = Publisher.objects.get_or_create(
            name=publisher_name,
            defaults={'slug': create_multilingual_slug(publisher_name)}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created publisher: {publisher.name}'))
        
        return publisher

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        # Detect encoding
        encoding = options['encoding']
        if not encoding:
            encoding = self.detect_encoding(csv_file)
            self.stdout.write(self.style.WARNING(f'Auto-detected encoding: {encoding}'))
        
        # Statistics
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        try:
            with open(csv_file, 'r', encoding=encoding) as file:
                # Remove BOM if present
                content = file.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                reader = csv.DictReader(content.splitlines())
                
                # Validate required columns
                required_fields = ['title', 'author', 'publisher', 'publication_year', 
                                 'classification_number', 'cutter_number', 'category', 
                                 'accession_number']
                
                missing_fields = [field for field in required_fields if field.rstrip('*') not in reader.fieldnames]
                if missing_fields:
                    raise CommandError(f'Missing required columns: {", ".join(missing_fields)}')
                
                self.stdout.write(self.style.SUCCESS(f'\n📚 Starting import from {csv_file}...\n'))
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        with transaction.atomic():
                            # Check if book with accession number already exists
                            accession_number = normalize_unicode_text(row.get('accession_number', '').strip())
                            if not accession_number:
                                self.stdout.write(
                                    self.style.ERROR(f'Row {row_num}: Missing accession_number')
                                )
                                error_count += 1
                                continue
                            
                            if Book.objects.filter(accession_number=accession_number).exists():
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Book with accession {accession_number} already exists. Skipping.')
                                )
                                skipped_count += 1
                                continue
                            
                            # Get related objects
                            authors = self.get_or_create_authors(row.get('author', ''))
                            category = self.get_or_create_category(row.get('category', ''))
                            publisher = self.get_or_create_publisher(row.get('publisher', ''))
                            
                            if not authors:
                                raise ValueError("At least one author is required")
                            
                            # Prepare book data
                            book_data = {
                                'title': normalize_unicode_text(row.get('title', '').strip()),
                                'title_bangla': normalize_unicode_text(row.get('title_bangla', '').strip()),
                                'subtitle': normalize_unicode_text(row.get('subtitle', '').strip()),
                                'subtitle_bangla': normalize_unicode_text(row.get('subtitle_bangla', '').strip()),
                                'accession_number': accession_number,
                                'volume': normalize_unicode_text(row.get('volume', '').strip()),
                                'publisher': publisher,
                                'publication_year': int(row.get('publication_year', 2024)),
                                'isbn_10': row.get('isbn_10', '').strip(),
                                'isbn_13': row.get('isbn_13', '').strip(),
                                'classification_number': row.get('classification_number', '').strip(),
                                'cutter_number': row.get('cutter_number', '').strip(),
                                'category': category,
                                'language': row.get('language', 'en').strip() or 'en',
                                'pages': int(row.get('pages', 0)) if row.get('pages', '').strip() else None,
                                'edition': normalize_unicode_text(row.get('edition', '').strip()),
                                'description': normalize_unicode_text(row.get('description', '').strip()),
                                'description_bangla': normalize_unicode_text(row.get('description_bangla', '').strip()),
                                'keywords': normalize_unicode_text(row.get('keywords', '').strip()),
                                'keywords_bangla': normalize_unicode_text(row.get('keywords_bangla', '').strip()),
                                'total_copies': int(row.get('total_copies', 1)),
                                'copies_available': int(row.get('copies_available', 1)),
                                'location_shelf': row.get('location_shelf', '').strip(),
                                'status': row.get('status', 'available').strip() or 'available',
                            }
                            
                            # Add price if provided
                            price = row.get('price', '').strip()
                            if price:
                                try:
                                    book_data['price'] = Decimal(price)
                                except:
                                    pass
                            
                            if not dry_run:
                                # Create book
                                book = Book.objects.create(**book_data)
                                
                                # Add authors (ManyToMany)
                                book.authors.set(authors)
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'✓ Row {row_num}: Created "{book.title}" ({book.accession_number})'
                                    )
                                )
                                success_count += 1
                            else:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'[DRY RUN] Row {row_num}: Would create "{book_data["title"]}" ({accession_number})'
                                    )
                                )
                                success_count += 1
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'✗ Row {row_num}: {str(e)}')
                        )
                        error_count += 1
                        continue
        
        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_file}')
        except Exception as e:
            raise CommandError(f'Error reading CSV: {str(e)}')
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n📊 Import Summary:'))
        self.stdout.write(f'  ✓ Successfully imported: {success_count}')
        self.stdout.write(f'  ⊘ Skipped (duplicates): {skipped_count}')
        self.stdout.write(f'  ✗ Errors: {error_count}')
        self.stdout.write('='*60 + '\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a DRY RUN. No data was saved.\n'))