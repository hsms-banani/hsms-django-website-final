#!/bin/bash

# HSMS Contact Form - Gmail Setup Helper Script
# This script will help you create the .env file with your Gmail credentials

echo "=========================================="
echo "  HSMS Contact Form - Gmail SMTP Setup"
echo "=========================================="
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  Warning: .env file already exists!"
    read -p "Do you want to overwrite it? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "Setup cancelled. Existing .env file preserved."
        exit 0
    fi
fi

echo "Step 1: Gmail App Password"
echo "---------------------------"
echo "Before proceeding, you need a Gmail App Password."
echo ""
echo "To generate one:"
echo "1. Go to: https://myaccount.google.com/apppasswords"
echo "2. Sign in to your Google account"
echo "3. Enable 2-Step Verification (if not already enabled)"
echo "4. Create an App Password for 'Mail' > 'Other (Custom)' > Name it 'HSMS Django'"
echo "5. Copy the 16-character password (format: abcd efgh ijkl mnop)"
echo ""
read -p "Press Enter when you have your App Password ready..."
echo ""

echo "Step 2: Enter Your Credentials"
echo "-------------------------------"

# Get Gmail address
read -p "Enter your Gmail address [hsmsmajorseminary@gmail.com]: " gmail_user
gmail_user=${gmail_user:-hsmsmajorseminary@gmail.com}

# Get App Password
echo ""
echo "Enter your Gmail App Password (the 16-character code from Step 1)"
echo "Paste it and press Enter:"
read -s app_password

# Validate input
if [ -z "$app_password" ]; then
    echo ""
    echo "❌ Error: App Password cannot be empty!"
    echo "Setup failed. Please run this script again."
    exit 1
fi

# Create .env file
echo ""
echo "Creating .env file..."

cat > .env << EOF
# Gmail SMTP Configuration for HSMS Django Project
# Generated: $(date)

GMAIL_USER=$gmail_user
GMAIL_APP_PASSWORD=$app_password
EOF

# Set proper permissions
chmod 600 .env

echo ""
echo "✅ Success! .env file created successfully!"
echo ""
echo "Next Steps:"
echo "1. Restart your Django server: python manage.py runserver"
echo "2. Test the contact form at: http://127.0.0.1:8000/contact/"
echo ""
echo "Security Note: Never commit the .env file to version control!"
echo "It's already in .gitignore, but be careful when sharing your code."
echo ""
