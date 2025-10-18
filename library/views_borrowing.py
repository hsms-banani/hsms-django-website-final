# library/views_borrowing.py
"""
Views for library borrowing system
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import timedelta
from .models import Book, BorrowRecord, LibrarySetting
from .email_service import LibraryEmailService

@login_required
def my_borrowed_books(request):
    """Display user's current and past borrowed books"""
    # Current active borrows
    active_borrows = BorrowRecord.objects.filter(
        borrower=request.user,
        status__in=['active', 'overdue']
    ).select_related('book__publisher', 'book__category').prefetch_related('book__authors').order_by('due_date')
    
    # Past borrows
    past_borrows = BorrowRecord.objects.filter(
        borrower=request.user,
        status='returned'
    ).select_related('book__publisher', 'book__category').prefetch_related('book__authors').order_by('-return_date')
    
    # Paginate past borrows
    paginator = Paginator(past_borrows, 10)
    page_number = request.GET.get('page')
    past_borrows_page = paginator.get_page(page_number)
    
    context = {
        'active_borrows': active_borrows,
        'past_borrows': past_borrows_page,
        'total_active': active_borrows.count(),
        'total_fines': sum(b.fine_amount for b in active_borrows if b.fine_amount > 0),
    }
    
    return render(request, 'library/my_borrowed_books.html', context)

from django.db import transaction

from django.conf import settings

@login_required
def borrow_book(request, slug):
    """Borrow a book"""
    book = get_object_or_404(Book, slug=slug)
    setting = LibrarySetting.objects.first()
    max_books_per_user = setting.max_books_per_user if setting else 5
    loan_period = setting.loan_period if setting else 14
    
    if request.method == 'POST':
        with transaction.atomic():
            # Re-fetch the book inside the transaction with select_for_update to lock the row
            book = Book.objects.select_for_update().get(pk=book.pk)

            # Check if book is available
            if not book.is_available:
                messages.error(request, 'This book is not available for borrowing.')
                return redirect('library:book_detail', slug=slug)
            
            # Check if user already has this book
            existing_borrow = BorrowRecord.objects.filter(
                borrower=request.user,
                book=book,
                status__in=['active', 'overdue']
            ).exists()
            
            if existing_borrow:
                messages.warning(request, 'You have already borrowed this book.')
                return redirect('library:my_borrowed_books')
            
            # Check borrowing limit
            active_count = BorrowRecord.objects.filter(
                borrower=request.user,
                status__in=['active', 'overdue']
            ).count()
            
            if active_count >= max_books_per_user:
                messages.error(request, f"You have reached the maximum borrowing limit of {max_books_per_user} books.")
                return redirect('library:my_borrowed_books')
            
            # Check for unpaid fines
            unpaid_fines = BorrowRecord.objects.filter(
                borrower=request.user,
                fine_amount__gt=0,
                fine_paid=False
            ).exists()
            
            if unpaid_fines:
                messages.error(request, 'Please pay your outstanding fines before borrowing more books.')
                return redirect('library:my_borrowed_books')
            
            # Create borrow record
            due_date = timezone.now().date() + timedelta(days=loan_period)
            
            borrow_record = BorrowRecord.objects.create(
                book=book,
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
        
        # Send confirmation email
        try:
            LibraryEmailService.send_borrow_confirmation(borrow_record)
        except Exception as e:
            # Log the error and notify the user that the email could not be sent
            messages.warning(request, "Book borrowed, but the confirmation email could not be sent.")
        
        messages.success(request, f'Book borrowed successfully! Due date: {due_date.strftime("%B %d, %Y")}')
        return redirect('library:my_borrowed_books')
    
    return redirect('library:book_detail', slug=slug)

from django.db import transaction

@login_required
def renew_book(request, record_id):
    """Renew a borrowed book"""
    record = get_object_or_404(BorrowRecord, id=record_id, borrower=request.user)
    setting = LibrarySetting.objects.first()
    renewal_period = setting.renewal_period if setting else 14
    
    if request.method == 'POST':
        with transaction.atomic():
            try:
                record.renew(days=renewal_period)
                messages.success(request, f'Book renewed successfully! New due date: {record.due_date.strftime("%B %d, %Y")}')
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('library:my_borrowed_books')

        try:
            LibraryEmailService.send_renewal_confirmation(record)
        except Exception as e:
            messages.warning(request, "Book renewed, but the confirmation email could not be sent.")
        
        return redirect('library:my_borrowed_books')
    
    new_due_date = record.due_date + timedelta(days=renewal_period)
    return render(request, 'library/renew_book_confirm.html', {'record': record, 'new_due_date': new_due_date})

@login_required
def return_book(request, record_id):
    """Return a borrowed book"""
    record = get_object_or_404(BorrowRecord, id=record_id, borrower=request.user)
    
    if request.method == 'POST':
        if record.status in ['returned', 'lost']:
            messages.warning(request, 'This book has already been processed.')
        else:
            with transaction.atomic():
                record.return_book()
            messages.success(request, 'Book returned successfully.')
        
        return redirect('library:my_borrowed_books')
    
    return render(request, 'library/return_book_confirm.html', {'record': record})

@login_required
def borrow_history(request):
    """View complete borrowing history with stats"""
    all_borrows = BorrowRecord.objects.filter(
        borrower=request.user
    ).select_related('book__publisher', 'book__category').prefetch_related('book__authors').order_by('-borrow_date')
    
    # Statistics
    total_borrowed = all_borrows.count()
    currently_borrowed = all_borrows.filter(status__in=['active', 'overdue']).count()
    total_returned = all_borrows.filter(status='returned').count()
    total_fines_paid = sum(b.fine_amount for b in all_borrows if b.fine_paid)
    total_fines_unpaid = sum(b.fine_amount for b in all_borrows if not b.fine_paid and b.fine_amount > 0)
    
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