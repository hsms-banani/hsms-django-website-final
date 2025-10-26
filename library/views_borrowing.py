# library/views_borrowing.py - ENHANCED VERSION
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import timedelta
from .models import Book, BorrowRecord, LibrarySetting
from .email_service import LibraryEmailService
from .decorators import library_user_required
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@library_user_required
def my_borrowed_books(request):
    """Display user's current and past borrowed books"""
    try:
        # Current active borrows
        active_borrows = BorrowRecord.objects.filter(
            borrower=request.user,
            status__in=['active', 'overdue']
        ).prefetch_related('publication').order_by('due_date')
        
        # Past borrows
        past_borrows = BorrowRecord.objects.filter(
            borrower=request.user,
            status='returned'
        ).prefetch_related('publication').order_by('-return_date')
        
        # Paginate past borrows
        paginator = Paginator(past_borrows, 10)
        page_number = request.GET.get('page')
        past_borrows_page = paginator.get_page(page_number)
        
        # Calculate statistics
        total_fines = sum(b.fine_amount for b in active_borrows if b.fine_amount > 0)
        
        context = {
            'active_borrows': active_borrows,
            'past_borrows': past_borrows_page,
            'total_active': active_borrows.count(),
            'total_fines': total_fines,
        }
        
        return render(request, 'library/my_borrowed_books.html', context)
    
    except Exception as e:
        logger.error(f"Error in my_borrowed_books for user {request.user.id}: {str(e)}")
        messages.error(request, "An error occurred while loading your borrowed books. Please try again.")
        return redirect('library:home')

@library_user_required
def borrow_book(request, slug):
    """Borrow a book with comprehensive validation"""
    if request.method != 'POST':
        messages.warning(request, 'Invalid request method.')
        return redirect('library:book_detail', slug=slug)
    
    try:
        with transaction.atomic():
            # Fetch book with lock
            book = get_object_or_404(
                Book.objects.select_for_update(),
                slug=slug
            )
            
            # Get library settings
            setting = LibrarySetting.objects.first()
            max_books = setting.max_books_per_user if setting else 5
            loan_period = setting.loan_period if setting else 14
            
            # Validation 1: Book availability
            if not book.is_available:
                messages.error(
                    request, 
                    f'"{book.title}" is currently not available. '
                    f'Available: {book.copies_available}/{book.total_copies}'
                )
                return redirect('library:book_detail', slug=slug)
            
            # Validation 2: Already borrowed this book
            content_type = ContentType.objects.get_for_model(book)
            existing_borrow = BorrowRecord.objects.filter(
                borrower=request.user,
                object_id=book.id,
                content_type=content_type,
                status__in=['active', 'overdue']
            ).exists()
            
            if existing_borrow:
                messages.warning(
                    request,
                    f'You have already borrowed "{book.title}". '
                    'Please return it before borrowing again.'
                )
                return redirect('library:my_borrowed_books')
            
            # Validation 3: Borrowing limit
            active_count = BorrowRecord.objects.filter(
                borrower=request.user,
                status__in=['active', 'overdue']
            ).count()
            
            if active_count >= max_books:
                messages.error(
                    request,
                    f'You have reached the maximum borrowing limit of {max_books} books. '
                    'Please return some books before borrowing more.'
                )
                return redirect('library:my_borrowed_books')
            
            # Validation 4: Unpaid fines
            unpaid_fines = BorrowRecord.objects.filter(
                borrower=request.user,
                fine_amount__gt=0,
                fine_paid=False
            )
            
            if unpaid_fines.exists():
                total_unpaid = sum(r.fine_amount for r in unpaid_fines)
                messages.error(
                    request,
                    f'You have unpaid fines totaling ৳{total_unpaid:.2f}. '
                    'Please pay your outstanding fines before borrowing more books.'
                )
                return redirect('library:my_borrowed_books')
            
            # Create borrow record
            due_date = timezone.now().date() + timedelta(days=loan_period)
            
            borrow_record = BorrowRecord.objects.create(
                publication=book,
                borrower=request.user,
                due_date=due_date,
                status='active'
            )
            
            # Update book availability
            book.copies_available -= 1
            book.times_borrowed += 1
            if book.copies_available == 0:
                book.status = 'checked_out'
            book.save()
            
            logger.info(
                f"Book borrowed: User {request.user.id} borrowed "
                f"'{book.title}' (ID: {book.id})"
            )
        
        # Send confirmation email (outside transaction)
        try:
            LibraryEmailService.send_borrow_confirmation(borrow_record)
        except Exception as e:
            logger.error(f"Email sending failed for borrow {borrow_record.id}: {str(e)}")
            messages.warning(
                request,
                "Book borrowed successfully, but confirmation email could not be sent."
            )
        
        messages.success(
            request,
            f'Successfully borrowed "{book.title}"! '
            f'Due date: {due_date.strftime("%B %d, %Y")}'
        )
        return redirect('library:my_borrowed_books')
    
    except Book.DoesNotExist:
        messages.error(request, 'Book not found.')
        return redirect('library:home')
    except Exception as e:
        logger.error(f"Error borrowing book {slug}: {str(e)}")
        messages.error(
            request,
            'An error occurred while borrowing the book. Please try again or contact the library.'
        )
        return redirect('library:book_detail', slug=slug)

@library_user_required
def renew_book(request, record_id):
    """Renew a borrowed book with validation"""
    try:
        record = get_object_or_404(
            BorrowRecord.objects.select_related('publication'),
            id=record_id,
            borrower=request.user
        )
        
        if request.method == 'POST':
            setting = LibrarySetting.objects.first()
            renewal_period = setting.renewal_period if setting else 14
            
            try:
                with transaction.atomic():
                    record.renew(days=renewal_period)
                
                # Send confirmation email
                try:
                    LibraryEmailService.send_renewal_confirmation(record)
                except Exception as e:
                    logger.error(f"Email sending failed for renewal {record.id}: {str(e)}")
                    messages.warning(
                        request,
                        "Book renewed successfully, but confirmation email could not be sent."
                    )
                
                messages.success(
                    request,
                    f'Successfully renewed "{record.publication.title}"! '
                    f'New due date: {record.due_date.strftime("%B %d, %Y")}'
                )
                return redirect('library:my_borrowed_books')
                
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('library:my_borrowed_books')
        
        # GET request - show confirmation page
        new_due_date = record.due_date + timedelta(
            days=setting.renewal_period if setting else 14
        )
        return render(request, 'library/renew_book_confirm.html', {
            'record': record,
            'new_due_date': new_due_date
        })
    
    except BorrowRecord.DoesNotExist:
        messages.error(request, 'Borrow record not found.')
        return redirect('library:my_borrowed_books')
    except Exception as e:
        logger.error(f"Error renewing book {record_id}: {str(e)}")
        messages.error(
            request,
            'An error occurred while renewing the book. Please try again.'
        )
        return redirect('library:my_borrowed_books')

@library_user_required
def return_book(request, record_id):
    """Return a borrowed book"""
    try:
        record = get_object_or_404(
            BorrowRecord.objects.select_related('publication'),
            id=record_id,
            borrower=request.user
        )

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    record.return_book()

                # Send confirmation email
                try:
                    LibraryEmailService.send_return_confirmation(record)
                except Exception as e:
                    logger.error(f"Email sending failed for return {record.id}: {str(e)}")
                    messages.warning(
                        request,
                        "Book returned successfully, but confirmation email could not be sent."
                    )

                messages.success(
                    request,
                    f'Successfully returned "{record.publication.title}"!'
                )
                return redirect('library:my_borrowed_books')

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('library:my_borrowed_books')

        # GET request - show confirmation page
        return render(request, 'library/return_book_confirm.html', {
            'record': record,
        })

    except BorrowRecord.DoesNotExist:
        messages.error(request, 'Borrow record not found.')
        return redirect('library:my_borrowed_books')
    except Exception as e:
        logger.error(f"Error returning book {record_id}: {str(e)}")
        messages.error(
            request,
            'An error occurred while returning the book. Please try again.'
        )
        return redirect('library:my_borrowed_books')


@library_user_required
def borrow_history(request):
    """View complete borrowing history with stats"""
    try:
        all_borrows = BorrowRecord.objects.filter(
            borrower=request.user
        ).prefetch_related('publication').order_by('-borrow_date')
        
        # Statistics
        total_borrowed = all_borrows.count()
        currently_borrowed = all_borrows.filter(status__in=['active', 'overdue']).count()
        total_returned = all_borrows.filter(status='returned').count()
        total_fines_paid = sum(b.fine_amount for b in all_borrows if b.fine_paid)
        total_fines_unpaid = sum(
            b.fine_amount for b in all_borrows 
            if not b.fine_paid and b.fine_amount > 0
        )
        
        # Pagination
        paginator = Paginator(all_borrows, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'stats': {
                'total_borrowed': total_borrowed,
                'currently_borrowed': currently_borrowed,
                'total_returned': total_returned,
                'total_fines_paid': total_fines_paid,
                'total_fines_unpaid': total_fines_unpaid,
            }
        }
        
        return render(request, 'library/borrow_history.html', context)
    
    except Exception as e:
        logger.error(f"Error in borrow_history for user {request.user.id}: {str(e)}")
        messages.error(request, "An error occurred while loading your history.")
        return redirect('library:my_borrowed_books')