# library/middleware.py
"""
Custom middleware for library security and logging
"""
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

class LibrarySecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enforce library-specific security rules
    """
    
    def process_request(self, request):
        """Process each request"""
        
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            return None
        
        # Prevent staff from using regular user features
        if request.user.is_staff and request.path.startswith('/library/my-books/'):
            messages.warning(
                request,
                "Staff members should use the admin panel to manage library operations."
            )
            return redirect('admin:index')
        
        # Prevent regular users from accessing staff features
        if not request.user.is_staff and request.path.startswith('/library/dashboard/'):
            messages.error(request, "You don't have permission to access this page.")
            return redirect('library:home')
        
        return None


class BorrowingActivityLogger(MiddlewareMixin):
    """
    Log all borrowing-related activities for audit trail
    """
    
    def process_response(self, request, response):
        """Log after response is generated"""
        
        # Only log POST requests for borrowing operations
        if request.method == 'POST' and request.user.is_authenticated:
            
            borrowing_paths = [
                '/library/borrow/',
                '/library/renew/',
                '/library/return/',
                '/library/dashboard/renew-book/',
                '/library/dashboard/return-book/',
            ]
            
            if any(request.path.startswith(path) for path in borrowing_paths):
                logger.info(
                    f"Borrowing Activity: User {request.user.id} ({request.user.username}) "
                    f"performed {request.path} - Status: {response.status_code}"
                )
        
        return response