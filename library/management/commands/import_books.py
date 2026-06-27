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
import re
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
            first_name_normalized = normalize_unicode_text(first_name)
            last_name_normalized = normalize_unicode_text(last_name)
            
            # Try to find author by normalized names
            author = Author.objects.filter(
                first_name__iexact=first_name_normalized,
                last_name__iexact=last_name_normalized
            ).first()

            if not author:
                base_slug = create_multilingual_slug(f"{first_name} {last_name}")
                slug = base_slug
                counter = 1
                while Author.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                author = Author.objects.create(
                    first_name=first_name_normalized,
                    last_name=last_name_normalized,
                    slug=slug
                )
                self.stdout.write(self.style.SUCCESS(f'  Created author: {author.full_name}'))
            
            authors.append(author)
        
        return authors

    def get_or_create_category(self, category_name):
        """Get or create category"""
        if not category_name:
            raise ValueError("Category is required")
        
        category_name_normalized = normalize_unicode_text(category_name)
        
        category = Category.objects.filter(name__iexact=category_name_normalized).first()
        
        if not category:
            base_slug = create_multilingual_slug(category_name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            category = Category.objects.create(
                name=category_name_normalized,
                slug=slug
            )
            self.stdout.write(self.style.SUCCESS(f'  Created category: {category.name}'))
        
        return category

    def get_or_create_publisher(self, publisher_name):
        """Get or create publisher"""
        if not publisher_name:
            raise ValueError("Publisher is required")
        
        publisher_name_normalized = normalize_unicode_text(publisher_name)
        
        publisher = Publisher.objects.filter(name__iexact=publisher_name_normalized).first()

        if not publisher:
            base_slug = create_multilingual_slug(publisher_name)
            slug = base_slug
            counter = 1
            while Publisher.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            publisher = Publisher.objects.create(
                name=publisher_name_normalized,
                slug=slug
            )
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
        error_messages = []
        
        try:
            with open(csv_file, 'r', encoding=encoding) as file:
                # Remove BOM if present
                content = file.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                
                reader = csv.DictReader(content.splitlines())
                # Validate required columns
                required_fields = ['title', 'author', 'publisher', 'publication_year', 
                                 'cutter_number', 'category', 'accession_number']
                
                fieldnames_without_star = [fn.rstrip('* ').lower() for fn in reader.fieldnames]
                has_classification = 'classification_number' in fieldnames_without_star or 'classification' in fieldnames_without_star
                
                missing_fields = [field for field in required_fields if field not in fieldnames_without_star]
                if not has_classification:
                    missing_fields.append('classification_number (or classification)')
                
                if missing_fields:
                    raise CommandError(f'Missing required columns: {", ".join(missing_fields)}')
                
                self.stdout.write(self.style.SUCCESS(f'\n📚 Starting import from {csv_file}...\n'))
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Check if row is completely empty
                        if not any(v.strip() for k, v in row.items() if k is not None and v is not None):
                            continue

                        # Clean row keys to avoid issues with or without asterisks, and make lowercase
                        clean_row = {str(k).rstrip('* ').strip().lower(): str(v) for k, v in row.items() if k is not None}

                        with transaction.atomic():
                            # Check if book with accession number already exists
                            accession_number = normalize_unicode_text(clean_row.get('accession_number', '').strip())
                            if not accession_number:
                                error_msg = f'Row {row_num}: Missing accession_number'
                                self.stdout.write(self.style.ERROR(error_msg))
                                error_messages.append(error_msg)
                                error_count += 1
                                continue
                            
                            if Book.objects.filter(accession_number=accession_number).exists():
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Book with accession {accession_number} already exists. Skipping.')
                                )
                                skipped_count += 1
                                continue
                            
                            # Get related objects
                            authors = self.get_or_create_authors(clean_row.get('author', ''))
                            category = self.get_or_create_category(clean_row.get('category', ''))
                            publisher = self.get_or_create_publisher(clean_row.get('publisher', ''))
                            
                            if not authors:
                                raise ValueError("At least one author is required")
                            
                            # Prepare book data
                            title = normalize_unicode_text(clean_row.get('title', '').strip())
                            title_bangla = normalize_unicode_text(clean_row.get('title_bangla', '').strip())

                            if not title and title_bangla:
                                title = title_bangla
                            
                            if not title:
                                raise ValueError("Title is required")

                            # Parse publication year robustly
                            pub_year_str = clean_row.get('publication_year', '').strip()
                            pub_year = 2024
                            if pub_year_str:
                                match = re.search(r'\d{4}', pub_year_str)
                                if match:
                                    extracted = int(match.group(0))
                                    if 1000 <= extracted <= 2025:
                                        pub_year = extracted

                            # Parse and fix Dewey Decimal classification number
                            classification = clean_row.get('classification_number', '')
                            if not classification:
                                classification = clean_row.get('classification', '')
                            classification = classification.strip()
                            
                            if not classification:
                                raise ValueError("Classification number is required")
                            
                            # Fix Dewey Decimal format issues caused by Excel
                            if classification.startswith('0.') and len(classification) >= 4 and classification[2].isdigit():
                                classification = classification[2:]
                                
                            parts = classification.split('.', 1)
                            if parts[0].isdigit():
                                parts[0] = parts[0].zfill(3)
                                classification = '.'.join(parts)

                            # Parse language safely
                            raw_lang = clean_row.get('language', 'en').strip().lower()
                            lang_map = {
                                'english': 'en', 'eng': 'en', 'en': 'en',
                                'bangla': 'bn', 'bengali': 'bn', 'bn': 'bn',
                                'hindi': 'hi', 'urdu': 'ur', 'arabic': 'ar'
                            }
                            language = lang_map.get(raw_lang, 'en')

                            # Parse status safely
                            raw_status = clean_row.get('status', 'available').strip().lower()
                            valid_statuses = [c[0] for c in Book.AVAILABILITY_STATUS]
                            status = raw_status if raw_status in valid_statuses else 'available'

                            book_data = {
                                'title': title,
                                'title_bangla': title_bangla,
                                'subtitle': normalize_unicode_text(clean_row.get('subtitle', '').strip()),
                                'subtitle_bangla': normalize_unicode_text(clean_row.get('subtitle_bangla', '').strip()),
                                'accession_number': accession_number,
                                'volume': normalize_unicode_text(clean_row.get('volume', '').strip()),
                                'publisher': publisher,
                                'publication_year': pub_year,
                                'isbn_10': clean_row.get('isbn_10', '').strip(),
                                'isbn_13': clean_row.get('isbn_13', '').strip(),
                                'classification_number': classification,
                                'cutter_number': clean_row.get('cutter_number', '').strip(),
                                'category': category,
                                'language': language,
                                'pages': 0,
                                'edition': normalize_unicode_text(clean_row.get('edition', '').strip()),
                                'description': normalize_unicode_text(clean_row.get('description', '').strip()),
                                'description_bangla': normalize_unicode_text(clean_row.get('description_bangla', '').strip()),
                                'keywords': normalize_unicode_text(clean_row.get('keywords', '').strip()),
                                'keywords_bangla': normalize_unicode_text(clean_row.get('keywords_bangla', '').strip()),
                                'total_copies': 1,
                                'copies_available': 1,
                                'location_shelf': clean_row.get('location_shelf', '').strip(),
                                'status': status,
                            }

                            # Safely parse numeric fields
                            try:
                                book_data['total_copies'] = int(clean_row.get('total_copies', 1))
                            except (ValueError, TypeError):
                                book_data['total_copies'] = 1

                            try:
                                book_data['copies_available'] = int(clean_row.get('copies_available', 1))
                            except (ValueError, TypeError):
                                book_data['copies_available'] = 1
                            
                            # Ensure copies available doesn't exceed total copies
                            if book_data['copies_available'] > book_data['total_copies']:
                                book_data['copies_available'] = book_data['total_copies']

                            # Handle pages with a regex to extract the main number
                            pages_str = clean_row.get('pages', '').strip()
                            if pages_str:
                                try:
                                    # Find the last number in the string
                                    page_numbers = re.findall(r'\d+', pages_str)
                                    if page_numbers:
                                        book_data['pages'] = int(page_numbers[-1])
                                except (ValueError, TypeError):
                                    book_data['pages'] = 0
                            
                            # Add price if provided
                            price = clean_row.get('price', '').strip()
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
                        error_msg = f'✗ Row {row_num}: {str(e)}'
                        self.stdout.write(self.style.ERROR(error_msg))
                        error_messages.append(error_msg)
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
        
        if error_messages:
            raise CommandError("\n".join(error_messages))

        if dry_run:
            self.stdout.write(self.style.WARNING('This was a DRY RUN. No data was saved.\n'))