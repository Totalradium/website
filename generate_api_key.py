#!/usr/bin/env python3
"""
Generate a secure API key for sync functionality
Run this script to generate your API key
"""

import secrets

def generate_api_key():
    """Generate a secure 64-character API key"""
    return secrets.token_hex(32)

def generate_django_secret_key():
    """Generate a secure Django SECRET_KEY"""
    return secrets.token_urlsafe(50)

if __name__ == "__main__":
    print("🔑 Generating secure keys for your hybrid app...")
    print()
    
    api_key = generate_api_key()
    secret_key = generate_django_secret_key()
    
    print("📋 Copy these keys to your environment variables:")
    print()
    print("SYNC_API_KEY =", api_key)
    print("SECRET_KEY =", secret_key)
    print()
    
    print("🚀 Next steps:")
    print("1. Add these to your local .env file")
    print("2. Add these to Render environment variables")
    print("3. Update your sync dashboard with the API key")
    print()
    print("⚠️  Keep these keys secret and never commit them to Git!")