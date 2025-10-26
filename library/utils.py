import logging

logger = logging.getLogger(__name__)

# library/utils.py
# Utility functions for Bangla/Unicode text handling

import re
import unicodedata
import hashlib
from django.utils.text import slugify
import csv
import random
import string
from io import StringIO
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

def detect_text_language(text):
    """
    Detect if text contains Bangla, English, or mixed content
    Returns: 'bn' for Bangla, 'en' for English, 'mixed' for both
    """
    if not text:
        return 'en'
    
    # Unicode range for Bengali script (0980-09FF)
    bangla_pattern = re.compile(r'[\u0980-\u09FF]')
    english_pattern = re.compile(r'[A-Za-z]')
    
    has_bangla = bangla_pattern.search(text)
    has_english = english_pattern.search(text)
    
    if has_bangla and has_english:
        return 'mixed'
    elif has_bangla:
        return 'bn'
    return 'en'

def normalize_unicode_text(text):
    """
    Normalize Unicode text for consistent handling
    This is crucial for Bangla text to prevent rendering issues
    """
    if not text:
        return ""
    
    # Remove BOM (Byte Order Mark) if present
    text = text.replace('\ufeff', '')
    
    # Normalize Unicode using NFC (Canonical Decomposition followed by Canonical Composition)
    # This is important for Bangla characters to display correctly
    text = unicodedata.normalize('NFC', text)
    
    # Remove extra whitespace but preserve single spaces
    text = ' '.join(text.split())
    
    return text.strip()

def create_multilingual_slug(text, fallback_text="", max_length=50):
    """
    Create URL-safe slug that works with Bangla and other Unicode text
    Falls back to hash-based approach for non-ASCII text
    """
    if not text and not fallback_text:
        return ""
    
    # Try the main text first
    text_to_slug = normalize_unicode_text(text) if text else ""
    
    # Try standard slugify first (works for English and some other scripts)
    slug = slugify(text_to_slug)
    
    if slug and len(slug) > 3:  # Minimum meaningful length
        return slug[:max_length]
    
    # For non-ASCII text (like pure Bangla), try fallback text
    if fallback_text:
        fallback_slug = slugify(normalize_unicode_text(fallback_text))
        if fallback_slug and len(fallback_slug) > 3:
            return fallback_slug[:max_length]
    
    # Last resort: create descriptive hash-based slug
    text_for_hash = text or fallback_text or "item"
    
    # Extract any English words for the base
    english_words = re.findall(r'[A-Za-z]+', text_for_hash)
    if english_words:
        base = slugify(' '.join(english_words[:2]))[:20]
    else:
        base = 'content'
    
    # Add hash for uniqueness
    hash_obj = hashlib.md5(text_for_hash.encode('utf-8'))
    hash_suffix = hash_obj.hexdigest()[:8]
    
    return f"{base}-{hash_suffix}"[:max_length]

def clean_csv_text(text):
    """
    Clean text from CSV imports to handle encoding issues
    Specifically designed for multilingual content
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Remove common encoding artifacts
    text = text.replace('\ufffd', '')  # Replacement character
    text = text.replace('\x00', '')   # Null bytes
    
    # Normalize Unicode
    text = normalize_unicode_text(text)
    
    return text

def format_multilingual_display(english_text, bangla_text, prefer_language='en'):
    """
    Format text for display based on language preference
    Returns tuple: (primary_text, secondary_text)
    """
    english_text = normalize_unicode_text(english_text or "")
    bangla_text = normalize_unicode_text(bangla_text or "")
    
    if prefer_language == 'bn':
        if bangla_text:
            return (bangla_text, english_text if english_text else None)
        else:
            return (english_text, None)
    else:  # Default to English
        if english_text:
            return (english_text, bangla_text if bangla_text else None)
        else:
            return (bangla_text, None)

def extract_search_terms(query):
    """
    Extract and normalize search terms from query
    Handles both English and Bangla text appropriately
    """
    if not query:
        return []
    
    query = normalize_unicode_text(query)
    
    # For Bangla text, split by spaces (Bangla doesn't use complex word boundaries like some scripts)
    # For English, use standard word splitting
    language = detect_text_language(query)
    
    if language == 'bn':
        # Simple space-based splitting for Bangla
        terms = [term.strip() for term in query.split() if term.strip()]
    else:
        # More sophisticated splitting for English/mixed content
        # Remove punctuation and split
        cleaned = re.sub(r'[^\w\s\u0980-\u09FF]', ' ', query, flags=re.UNICODE)
        terms = [term.strip() for term in cleaned.split() if term.strip() and len(term) >= 2]
    
    return terms

def validate_bangla_text(text):
    """
    Validate if Bangla text is properly encoded and displayable
    Returns: (is_valid, error_message)
    """
    if not text:
        return (True, None)
    
    try:
        # Try to normalize - this will fail if there are encoding issues
        normalized = unicodedata.normalize('NFC', text)
        
        # Check for replacement characters or null bytes
        if '\ufffd' in normalized or '\x00' in normalized:
            return (False, "Text contains invalid characters")
        
        # Check if text contains valid Bangla characters
        bangla_pattern = re.compile(r'[\u0980-\u09FF]')
        if not bangla_pattern.search(normalized):
            return (False, "No valid Bangla characters found")
        
        return (True, None)
        
    except UnicodeError as e:
        return (False, f"Unicode error: {str(e)}")
    except Exception as e:
        return (False, f"Validation error: {str(e)}")

def suggest_font_for_text(text):
    """
    Suggest appropriate font family based on text content
    Returns CSS font-family string
    """
    if not text:
        return "'Inter', sans-serif"
    
    language = detect_text_language(text)
    
    if language == 'bn':
        return "'Noto Sans Bengali', 'SutonnyMJ', 'Kalpurush', sans-serif"
    elif language == 'mixed':
        return "'Inter', 'Noto Sans Bengali', system-ui, sans-serif"
    else:
        return "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"

def generate_search_variants(query):
    """
    Generate search variants for better matching
    Useful for handling different spellings or romanization
    """
    variants = [query]
    
    # Add normalized version
    normalized = normalize_unicode_text(query)
    if normalized != query:
        variants.append(normalized)
    
    # Add lowercase version
    lower_query = query.lower()
    if lower_query != query:
        variants.append(lower_query)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for variant in variants:
        if variant not in seen and variant:
            seen.add(variant)
            unique_variants.append(variant)
    
    return unique_variants

# Template filter functions
def get_display_language_class(text):
    """
    Get CSS class for text based on detected language
    For use in templates
    """
    language = detect_text_language(text)
    return {
        'bn': 'bangla',
        'mixed': 'mixed-content',
        'en': 'english'
    }.get(language, 'english')

def truncate_multilingual(text, length=100, language='auto'):
    """
    Truncate text appropriately for different languages
    Bangla characters may need different truncation logic
    """
    if not text:
        return ""
    
    text = normalize_unicode_text(text)
    
    if len(text) <= length:
        return text
    
    if language == 'auto':
        language = detect_text_language(text)
    
    # For Bangla, be more conservative with truncation
    # as characters may be visually wider
    if language == 'bn':
        effective_length = int(length * 0.8)
    else:
        effective_length = length
    
    if len(text) <= effective_length:
        return text
    
    # Find a good break point (space or punctuation)
    truncated = text[:effective_length]
    
    # Look for last space within reasonable range
    last_space = truncated.rfind(' ')
    if last_space > effective_length * 0.7:
        return truncated[:last_space] + '...'
    
    return truncated + '...'



def generate_random_password(length=12):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(characters) for _ in range(length))
    
    # Ensure password has required character types
    if not any(c.isupper() for c in password):
        password = password[:-1] + random.choice(string.ascii_uppercase)
    if not any(c.isdigit() for c in password):
        password = password[:-1] + random.choice(string.digits)
    if not any(c in "!@#$%^&*" for c in password):
        password = password[:-1] + random.choice("!@#$%^&*")
    
    return password


def generate_username_from_name(first_name, last_name, email=None):
    """Generate a unique username from name"""
    # Clean and normalize names
    first_name = unicodedata.normalize('NFKD', first_name.lower()).encode('ascii', 'ignore').decode('ascii')
    last_name = unicodedata.normalize('NFKD', last_name.lower()).encode('ascii', 'ignore').decode('ascii')
    
    # Remove special characters
    first_name = ''.join(c for c in first_name if c.isalnum())
    last_name = ''.join(c for c in last_name if c.isalnum())
    
    # Try different username patterns
    base_username = f"{first_name}.{last_name}"
    username = base_username
    
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
        
        # Safety check to avoid infinite loop
        if counter > 1000:
            # Use email-based username as fallback
            if email:
                username = email.split('@')[0] + str(random.randint(1000, 9999))
            else:
                username = f"user{random.randint(10000, 99999)}"
            break
    
    return username



def validate_user_row(row, row_number):
    """Validate a single row of user data"""
    errors = []
    
    # Required fields validation
    if not row.get('first_name', '').strip():
        errors.append(f"Row {row_number}: First name is required")
    elif len(row['first_name'].strip()) > 150:
        errors.append(f"Row {row_number}: First name too long (max 150 characters)")
    
    if not row.get('last_name', '').strip():
        errors.append(f"Row {row_number}: Last name is required")
    elif len(row['last_name'].strip()) > 150:
        errors.append(f"Row {row_number}: Last name too long (max 150 characters)")
    
    # Email validation
    email = row.get('email', '').strip()
    if not email:
        errors.append(f"Row {row_number}: Email is required")
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors.append(f"Row {row_number}: Invalid email format: {email}")
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            errors.append(f"Row {row_number}: Email already exists: {email}")
    
    # Username validation (if provided)
    username = row.get('username', '').strip()
    if username:
        if len(username) > 150:
            errors.append(f"Row {row_number}: Username too long (max 150 characters)")
        elif not username.isalnum() and '_' not in username and '.' not in username:
            errors.append(f"Row {row_number}: Username can only contain letters, numbers, dots, and underscores")
        elif User.objects.filter(username=username).exists():
            errors.append(f"Row {row_number}: Username already exists: {username}")
    
    return errors



def process_bulk_user_csv(csv_file, imported_by):
    """Process CSV file and create users with comprehensive error handling"""
    from .models import BulkUserImportLog, LibraryPasswordSettings
    
    # Get default password
    password_settings = LibraryPasswordSettings.objects.first()
    default_password = password_settings.default_password if password_settings else None

    # Read CSV content with encoding detection
    try:
        content = csv_file.read().decode('utf-8-sig')  # Handle BOM
    except UnicodeDecodeError:
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('cp1252')
        except Exception:
            try:
                csv_file.seek(0)
                content = csv_file.read().decode('latin-1')
            except Exception as e:
                logger.error(f"CSV encoding error: {str(e)}")
                raise ValidationError(
                    "Could not decode CSV file. Please ensure it's saved as UTF-8."
                )
    
    csv_reader = csv.DictReader(StringIO(content))
    
    # Validate headers
    expected_headers = ['first_name', 'last_name', 'email', 'username']
    actual_headers = [header.strip().replace('*', '') for header in csv_reader.fieldnames]
    
    if not all(h in actual_headers for h in expected_headers[:3]):  # first 3 are required
        raise ValidationError(
            f"Invalid CSV headers. Expected at least: first_name, last_name, email. "
            f"Found: {', '.join(actual_headers)}"
        )
    
    # Initialize counters and logs
    total_records = 0
    successful_imports = 0
    failed_imports = 0
    error_log = []
    success_log = []
    created_users = []
    
    # Validate all rows first
    rows_to_process = []
    for row_num, row in enumerate(csv_reader, start=2):
        total_records += 1
        
        # Skip empty rows
        if not any(row.values()):
            continue
        
        # Clean row data
        cleaned_row = {
            k.strip().replace('*', ''): v.strip() if v else '' 
            for k, v in row.items() if k
        }
        
        # Validate row
        validation_errors = validate_user_row(cleaned_row, row_num)
        if validation_errors:
            failed_imports += 1
            error_log.extend(validation_errors)
        else:
            rows_to_process.append((row_num, cleaned_row))
    
    # Process valid rows
    for row_num, cleaned_row in rows_to_process:
        try:
            # Generate username if not provided
            username = cleaned_row.get('username', '').strip()
            if not username:
                username = generate_username_from_name(
                    cleaned_row['first_name'],
                    cleaned_row['last_name'],
                    cleaned_row['email']
                )
            
            # Double-check username uniqueness
            if User.objects.filter(username=username).exists():
                username = generate_username_from_name(
                    cleaned_row['first_name'],
                    cleaned_row['last_name'],
                    cleaned_row['email']
                )
            
            # Use default password or generate a random one
            password = default_password or generate_random_password()
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=cleaned_row['email'],
                password=password,
                first_name=cleaned_row['first_name'],
                last_name=cleaned_row['last_name'],
                is_staff=False,
                is_superuser=False,
                is_active=True
            )
            
            successful_imports += 1
            success_log.append(
                f"Row {row_num}: Created user '{username}' - "
                f"{cleaned_row['first_name']} {cleaned_row['last_name']} "
                f"({cleaned_row['email']})"
            )
            
            # Store for credentials export
            created_users.append({
                'username': username,
                'password': password,
                'email': cleaned_row['email'],
                'first_name': cleaned_row['first_name'],
                'last_name': cleaned_row['last_name'],
                'row_number': row_num
            })
            
            logger.info(f"User created: {username} ({cleaned_row['email']})")
            
        except Exception as e:
            failed_imports += 1
            error_msg = f"Row {row_num}: Error creating user - {str(e)}"
            error_log.append(error_msg)
            logger.error(error_msg)
    
    # Create import log
    import_log = BulkUserImportLog.objects.create(
        imported_by=imported_by,
        csv_file=csv_file,
        total_records=total_records,
        successful_imports=successful_imports,
        failed_imports=failed_imports,
        error_log='\n'.join(error_log) if error_log else 'No errors',
        success_log='\n'.join(success_log) if success_log else 'No successful imports'
    )
    
    return {
        'import_log': import_log,
        'created_users': created_users,
        'total_records': total_records,
        'successful_imports': successful_imports,
        'failed_imports': failed_imports
    }


def generate_credentials_csv(users_data):
    """Generate CSV with user credentials"""
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header with instructions
    writer.writerow([
        'Username', 'Password', 'Email', 'First Name', 'Last Name',
        'Status', 'Login URL', 'Row Number'
    ])
    
    # Write user data
    for user in users_data:
        writer.writerow([
            user['username'],
            user['password'],
            user['email'],
            user['first_name'],
            user['last_name'],
            'Active',
            'https://hsms-banani.org/login/',  # Update with your actual URL
            user.get('row_number', '')
        ])
    
    return output.getvalue()