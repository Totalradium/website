#!/usr/bin/env python3
import os
import sys

def find_null_bytes_in_files(directory):
    """Find Python files containing null bytes"""
    corrupted_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        skip_dirs = ['whatsapp_profile', 'whatsapp_profile_chrome', 'media', '__pycache__', '.git']
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        if b'\x00' in content:
                            corrupted_files.append(file_path)
                            print(f"FOUND NULL BYTES: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return corrupted_files

if __name__ == "__main__":
    directory = "."
    print("Scanning for Python files with null bytes...")
    corrupted = find_null_bytes_in_files(directory)
    
    if corrupted:
        print(f"\nFound {len(corrupted)} corrupted files:")
        for file in corrupted:
            print(f"  - {file}")
    else:
        print("\nNo corrupted files found.")