# library/views_dashboard.py - New file for enhanced dashboard views

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum, Prefetch
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta, date
from .models import Book, BorrowRecord, LibrarySetting, User, Periodical
from .email_service import LibraryEmailService
import csv
import logging

logger = logging.getLogger(__name__)


@staff_member_required
def enhanced_dashboard(request):
    """Enhanced librarian dashboard with comprehensive tools"""
    
    # Get date range for filtering
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Core Statistics
    total_publications = Book.objects.count() + Periodical.objects.count()
    total_books = Book.objects.count()
    available_books = Book.objects.filter(status='available', copies_available__gt=0).count()
    
    # Borrowing Statistics
    active_borrows = BorrowRecord.objects.filter(status__in=['active', 'overdue'])
    borrowed_count = active_borrows.count()
    overdue_count = BorrowRecord.objects.filter(status='overdue').count()
    
    # Today's Activity
    today_borrows = BorrowRecord.objects.filter(
        borrow_date__date=today
    ).select_related('borrower').prefetch_related('publication')
    
    today_returns = BorrowRecord.objects.filter(
        return_date__date=today
    ).select_related('borrower').prefetch_related('publication')
    
    today_due = BorrowRecord.objects.filter(
        due_date=today,
        status='active'
    ).select_related('borrower').prefetch_related('publication')
    
    # Users Statistics
    total_users = User.objects.filter(is_staff=False, is_superuser=False).count()
    active_borrowers = active_borrows.values('borrower').distinct().count()
    
    # Financial Statistics
    total_fines = BorrowRecord.objects.filter(
        fine_amount__gt=0
    ).aggregate(total=Sum('fine_amount'))['total'] or 0
    
    unpaid_fines = BorrowRecord.objects.filter(
        fine_amount__gt=0,
        fine_paid=False
    ).aggregate(total=Sum('fine_amount'))['total'] or 0
    
    # Due Soon (Next 7 Days)
    seven_days = today + timedelta(days=7)
    due_soon = BorrowRecord.objects.filter(
        status='active',
        due_date__lte=seven_days,
        due_date__gte=today
    ).select_related('borrower').prefetch_related('publication').order_by('due_date')
    
    # Recent Overdue
    recent_overdue = BorrowRecord.objects.filter(
        status='overdue'
    ).select_related('borrower').prefetch_related('publication').order_by('-due_date')[:10]
    
    # Popular Books (This Month)
    popular_books = Book.objects.filter(
        times_borrowed__gt=0
    ).order_by('-times_borrowed')[:10]
    
    # Low Stock Alert
    low_stock = Book.objects.filter(
        copies_available__lte=1,
        total_copies__gt=1
    ).order_by('copies_available')[:10]
    
    # Top Borrowers (This Month)
    top_borrowers = User.objects.filter(
        is_staff=False,
        borrowed_record__borrow_date__gte=thirty_days_ago
    ).annotate(
        recent_borrows=Count('borrowed_record')
    ).order_by('-recent_borrows')[:10]
    
    # Get library settings for default values
    settings = LibrarySetting.objects.first()
    
    context = {
        # Statistics
        'total_publications': total_publications,
        'total_books': total_books,
        'available_books': available_books,
        'borrowed_count': borrowed_count,
        'overdue_count': overdue_count,
        'total_users': total_users,
        'active_borrowers': active_borrowers,
        'total_fines': total_fines,
        'unpaid_fines': unpaid_fines,
        
        # Today's Activity
        'today_borrows': today_borrows,
        'today_returns': today_returns,
        'today_due': today_due,
        'today_borrow_count': today_borrows.count(),
        'today_return_count': today_returns.count(),
        'today_due_count': today_due.count(),
        
        # Tables
        'due_soon': due_soon,
        'recent_overdue': recent_overdue,
        'popular_books': popular_books,
        'low_stock': low_stock,
        'top_borrowers': top_borrowers,
        
        # Settings
        'library_settings': settings,
        
        # Date
        'today': today,
    }
    
    return render(request, 'library/enhanced_dashboard.html', context)


@staff_member_required
def quick_search_dashboard(request):
    """Quick search for books, users, and borrow records"""
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')  # all, books, users, borrows
    
    results = {
        'books': [],
        'users': [],
        'borrows': [],
        'query': query
    }
    
    if len(query) < 2:
        return render(request, 'library/partials/dashboard_search_results.html', results)
    
    # Search Books
    if search_type in ['all', 'books']:
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(accession_number__icontains=query) |
            Q(isbn_10__icontains=query) |
            Q(isbn_13__icontains=query) |
            Q(call_number__icontains=query) |
            Q(authors__first_name__icontains=query) |
            Q(authors__last_name__icontains=query)
        ).distinct().select_related('publisher', 'category').prefetch_related('authors')[:10]
        results['books'] = books
    
    # Search Users
    if search_type in ['all', 'users']:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query),
            is_staff=False
        )[:10]
        results['users'] = users
    
    # Search Active Borrows
    if search_type in ['all', 'borrows']:
        book_type = ContentType.objects.get_for_model(Book)
        borrows = BorrowRecord.objects.filter(
            Q(borrower__username__icontains=query) |
            Q(borrower__email__icontains=query) |
            Q(borrower__first_name__icontains=query) |
            Q(borrower__last_name__icontains=query),
            status__in=['active', 'overdue']
        ).select_related('borrower').prefetch_related('publication')[:10]
        results['borrows'] = borrows
    
    return render(request, 'library/partials/dashboard_search_results.html', results)


@staff_member_required
def manual_borrow_search(request):
    """Search for book to manually record borrowing"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'books': []})
    
    books = Book.objects.filter(
        Q(title__icontains=query) |
        Q(accession_number__icontains=query) |
        Q(call_number__icontains=query) |
        Q(isbn_10__icontains=query) |
        Q(isbn_13__icontains=query),
        status='available',
        copies_available__gt=0
    ).select_related('publisher', 'category').prefetch_related('authors')[:15]
    
    books_data = [{
        'id': book.id,
        'title': book.title,
        'accession_number': book.accession_number,
        'call_number': book.call_number,
        'authors': ', '.join([a.full_name for a in book.authors.all()]),
        'available': book.copies_available,
        'total': book.total_copies
    } for book in books]
    
    return JsonResponse({'books': books_data})


@staff_member_required
def manual_borrow_user_search(request):
    """Search for user to manually record borrowing"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(email__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query),
        is_staff=False,
        is_active=True
    )[:15]
    
    users_data = [{
        'id': user.id,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'email': user.email,
        'active_borrows': BorrowRecord.objects.filter(
            borrower=user,
            status__in=['active', 'overdue']
        ).count()
    } for user in users]
    
    return JsonResponse({'users': users_data})


@staff_member_required
def process_manual_borrow(request):
    """Process manual book borrowing"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    book_id = request.POST.get('book_id')
    user_id = request.POST.get('user_id')
    due_date_str = request.POST.get('due_date')
    
    if not all([book_id, user_id, due_date_str]):
        return JsonResponse({
            'success': False,
            'error': 'Missing required fields'
        }, status=400)
    
    try:
        with transaction.atomic():
            book = get_object_or_404(Book.objects.select_for_update(), id=book_id)
            user = get_object_or_404(User, id=user_id)
            
            # Parse due date
            try:
                due_date = timezone.datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format'
                }, status=400)
            
            # Validate book availability
            if not book.is_available:
                return JsonResponse({
                    'success': False,
                    'error': f'Book not available. Available: {book.copies_available}/{book.total_copies}'
                }, status=400)
            
            # Check borrowing limit
            settings = LibrarySetting.objects.first()
            max_books = settings.max_books_per_user if settings else 5
            
            active_count = BorrowRecord.objects.filter(
                borrower=user,
                status__in=['active', 'overdue']
            ).count()
            
            if active_count >= max_books:
                return JsonResponse({
                    'success': False,
                    'error': f'User has reached borrowing limit ({max_books} books)'
                }, status=400)
            
            # Check for unpaid fines
            unpaid_fines = BorrowRecord.objects.filter(
                borrower=user,
                fine_amount__gt=0,
                fine_paid=False
            ).exists()
            
            if unpaid_fines:
                return JsonResponse({
                    'success': False,
                    'error': 'User has unpaid fines'
                }, status=400)
            
            # Create borrow record
            borrow_record = BorrowRecord.objects.create(
                publication=book,
                borrower=user,
                due_date=due_date,
                status='active'
            )
            
            # Update book
            book.copies_available -= 1
            book.times_borrowed += 1
            if book.copies_available == 0:
                book.status = 'checked_out'
            book.save()
            
            logger.info(
                f"Manual borrow: Staff {request.user.id} recorded borrow for "
                f"User {user.id} - Book {book.id}"
            )
            
            # Send confirmation email
            try:
                LibraryEmailService.send_borrow_confirmation(borrow_record)
            except Exception as e:
                logger.error(f"Email failed for borrow {borrow_record.id}: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully borrowed "{book.title}" to {user.get_full_name()}',
                'borrow_id': borrow_record.id
            })
            
    except Exception as e:
        logger.error(f"Error in manual borrow: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


@staff_member_required
def dashboard_action_renew(request, record_id):
    """Quick renew action from dashboard"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        record = get_object_or_404(BorrowRecord, id=record_id)
        settings = LibrarySetting.objects.first()
        renewal_days = settings.renewal_period if settings else 14
        
        record.renew(days=renewal_days)
        
        # Send confirmation
        try:
            LibraryEmailService.send_renewal_confirmation(record)
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'message': f'Book renewed. New due date: {record.due_date.strftime("%b %d, %Y")}',
            'new_due_date': record.due_date.strftime("%Y-%m-%d")
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error renewing record {record_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@staff_member_required
def dashboard_action_return(request, record_id):
    """Quick return action from dashboard"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        with transaction.atomic():
            record = get_object_or_404(BorrowRecord, id=record_id)
            record.return_book()
            
            # Send confirmation
            try:
                LibraryEmailService.send_return_confirmation(record)
            except:
                pass
            
            fine_message = ''
            if record.fine_amount > 0:
                fine_message = f' Fine: ৳{record.fine_amount:.2f}'
            
            return JsonResponse({
                'success': True,
                'message': f'Book returned successfully.{fine_message}',
                'had_fine': record.fine_amount > 0,
                'fine_amount': float(record.fine_amount)
            })
            
    except Exception as e:
        logger.error(f"Error returning record {record_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@staff_member_required
def dashboard_action_reminder(request, record_id):
    """Send reminder email"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        record = get_object_or_404(BorrowRecord, id=record_id)
        
        if record.status == 'overdue':
            LibraryEmailService.send_overdue_notice(record)
            message = 'Overdue notice sent'
        elif record.days_until_due and record.days_until_due <= 1:
            LibraryEmailService.send_second_reminder(record)
            message = 'Urgent reminder sent'
        else:
            LibraryEmailService.send_first_reminder(record)
            message = 'Reminder sent'
        
        return JsonResponse({
            'success': True,
            'message': f'{message} to {record.borrower.email}'
        })
        
    except Exception as e:
        logger.error(f"Error sending reminder for record {record_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to send email'}, status=500)


@staff_member_required
def dashboard_mark_fine_paid(request, record_id):
    """Mark fine as paid"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        record = get_object_or_404(BorrowRecord, id=record_id)
        record.fine_paid = True
        record.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Fine of ৳{record.fine_amount:.2f} marked as paid'
        })
        
    except Exception as e:
        logger.error(f"Error marking fine paid for record {record_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@staff_member_required
def get_active_borrows_table(request):
    """Get active borrows table with search/filter"""
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')  # all, active, overdue
    
    borrows = BorrowRecord.objects.filter(
        status__in=['active', 'overdue']
    ).select_related('borrower').prefetch_related('publication')
    
    # Apply status filter
    if status_filter == 'active':
        borrows = borrows.filter(status='active')
    elif status_filter == 'overdue':
        borrows = borrows.filter(status='overdue')
    
    # Apply search
    if query:
        book_type = ContentType.objects.get_for_model(Book)
        borrows = borrows.filter(
            Q(borrower__username__icontains=query) |
            Q(borrower__email__icontains=query) |
            Q(borrower__first_name__icontains=query) |
            Q(borrower__last_name__icontains=query) |
            Q(object_id__in=Book.objects.filter(
                Q(title__icontains=query) |
                Q(accession_number__icontains=query)
            ).values('id'))
        )
    
    borrows = borrows.order_by('due_date')
    
    # Paginate
    paginator = Paginator(borrows, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'library/partials/active_borrows_table.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter
    })


@staff_member_required
def bulk_send_reminders(request):
    """Send reminders to multiple borrowers"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    record_ids = request.POST.getlist('record_ids[]')
    
    if not record_ids:
        return JsonResponse({'success': False, 'error': 'No records selected'}, status=400)
    
    sent_count = 0
    error_count = 0
    
    for record_id in record_ids:
        try:
            record = BorrowRecord.objects.get(id=record_id)
            
            if record.status == 'overdue':
                LibraryEmailService.send_overdue_notice(record)
            elif record.days_until_due and record.days_until_due <= 3:
                LibraryEmailService.send_first_reminder(record)
            
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send reminder for record {record_id}: {str(e)}")
            error_count += 1
    
    return JsonResponse({
        'success': True,
        'message': f'Sent {sent_count} reminders. {error_count} failed.',
        'sent': sent_count,
        'failed': error_count
    })


@staff_member_required
def export_current_borrows(request):
    """Export current active/overdue borrows to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="active_borrows_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Book Title', 'Accession No', 'Borrower Name', 'Email',
        'Borrow Date', 'Due Date', 'Status', 'Days Overdue', 'Fine'
    ])
    
    borrows = BorrowRecord.objects.filter(
        status__in=['active', 'overdue']
    ).select_related('borrower').prefetch_related('publication')
    
    for record in borrows:
        publication = record.publication
        days_overdue = 0
        if record.status == 'overdue':
            days_overdue = (timezone.now().date() - record.due_date).days
        
        writer.writerow([
            publication.title if publication else 'N/A',
            publication.accession_number if publication else 'N/A',
            record.borrower.get_full_name(),
            record.borrower.email,
            record.borrow_date.strftime('%Y-%m-%d'),
            record.due_date.strftime('%Y-%m-%d'),
            record.get_status_display(),
            days_overdue if days_overdue > 0 else '',
            f'{record.fine_amount:.2f}' if record.fine_amount > 0 else ''
        ])
    
    return response