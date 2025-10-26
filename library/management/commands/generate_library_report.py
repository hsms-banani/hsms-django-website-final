# library/management/commands/generate_library_report.py
"""
Generate comprehensive library usage reports
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from datetime import timedelta
from library.models import Book, BorrowRecord, Category, Author
import csv

class Command(BaseCommand):
    help = 'Generate comprehensive library usage report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            default='month',
            help='Report period: week, month, quarter, year'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='library_report.csv',
            help='Output file path'
        )

    def handle(self, *args, **options):
        period = options['period']
        output_file = options['output']
        
        # Calculate date range
        today = timezone.now().date()
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)
        
        self.stdout.write(f'Generating report from {start_date} to {today}')
        
        # Collect statistics
        stats = self.collect_statistics(start_date, today)
        
        # Write to CSV
        self.write_report(output_file, stats, period)
        
        self.stdout.write(
            self.style.SUCCESS(f'Report generated successfully: {output_file}')
        )
    
    def collect_statistics(self, start_date, end_date):
        """Collect comprehensive statistics"""
        
        # Borrowing statistics
        borrows_in_period = BorrowRecord.objects.filter(
            borrow_date__range=[start_date, end_date]
        )
        
        total_borrows = borrows_in_period.count()
        unique_borrowers = borrows_in_period.values('borrower').distinct().count()
        
        returns_in_period = BorrowRecord.objects.filter(
            return_date__range=[start_date, end_date],
            status='returned'
        )
        
        total_returns = returns_in_period.count()
        
        # Overdue statistics
        overdue_count = BorrowRecord.objects.filter(
            status='overdue'
        ).count()
        
        total_fines = BorrowRecord.objects.filter(
            fine_amount__gt=0
        ).aggregate(total=Sum('fine_amount'))['total'] or 0
        
        unpaid_fines = BorrowRecord.objects.filter(
            fine_amount__gt=0,
            fine_paid=False
        ).aggregate(total=Sum('fine_amount'))['total'] or 0
        
        # Popular books
        popular_books = Book.objects.annotate(
            borrows=Count('borrow_records')
        ).filter(
            borrows__gt=0
        ).order_by('-borrows')[:10]
        
        # Category statistics
        category_stats = Category.objects.annotate(
            total_books=Count('book_publications'),
            times_borrowed=Sum('book_publications__times_borrowed')
        ).filter(times_borrowed__gt=0).order_by('-times_borrowed')[:10]
        
        # Author statistics
        author_stats = Author.objects.annotate(
            total_books=Count('publications'),
            times_borrowed=Sum('publications__times_borrowed')
        ).filter(times_borrowed__gt=0).order_by('-times_borrowed')[:10]
        
        return {
            'period': {
                'start': start_date,
                'end': end_date
            },
            'borrowing': {
                'total_borrows': total_borrows,
                'unique_borrowers': unique_borrowers,
                'total_returns': total_returns,
                'overdue_count': overdue_count
            },
            'financial': {
                'total_fines': total_fines,
                'unpaid_fines': unpaid_fines
            },
            'popular_books': popular_books,
            'top_categories': category_stats,
            'top_authors': author_stats
        }
    
    def write_report(self, output_file, stats, period):
        """Write statistics to CSV file"""
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['LIBRARY USAGE REPORT'])
            writer.writerow([f"Period: {period.upper()}"])
            writer.writerow([f"From: {stats['period']['start']}"])
            writer.writerow([f"To: {stats['period']['end']}"])
            writer.writerow([])
            
            # Borrowing Statistics
            writer.writerow(['BORROWING STATISTICS'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Borrows', stats['borrowing']['total_borrows']])
            writer.writerow(['Unique Borrowers', stats['borrowing']['unique_borrowers']])
            writer.writerow(['Total Returns', stats['borrowing']['total_returns']])
            writer.writerow(['Currently Overdue', stats['borrowing']['overdue_count']])
            writer.writerow([])
            
            # Financial Statistics
            writer.writerow(['FINANCIAL STATISTICS'])
            writer.writerow(['Metric', 'Amount (BDT)'])
            writer.writerow(['Total Fines', f"{stats['financial']['total_fines']:.2f}"])
            writer.writerow(['Unpaid Fines', f"{stats['financial']['unpaid_fines']:.2f}"])
            writer.writerow([])
            
            # Popular Books
            writer.writerow(['TOP 10 POPULAR BOOKS'])
            writer.writerow(['Rank', 'Title', 'Author(s)', 'Times Borrowed'])
            for idx, book in enumerate(stats['popular_books'], 1):
                writer.writerow([
                    idx,
                    book.title,
                    book.authors_list,
                    book.times_borrowed
                ])
            writer.writerow([])
            
            # Top Categories
            writer.writerow(['TOP 10 CATEGORIES'])
            writer.writerow(['Rank', 'Category', 'Total Books', 'Times Borrowed'])
            for idx, cat in enumerate(stats['top_categories'], 1):
                writer.writerow([
                    idx,
                    cat.name,
                    cat.total_books,
                    cat.times_borrowed or 0
                ])
            writer.writerow([])
            
            # Top Authors
            writer.writerow(['TOP 10 AUTHORS'])
            writer.writerow(['Rank', 'Author', 'Total Books', 'Times Borrowed'])
            for idx, author in enumerate(stats['top_authors'], 1):
                writer.writerow([
                    idx,
                    author.full_name,
                    author.total_books,
                    author.times_borrowed or 0
                ])