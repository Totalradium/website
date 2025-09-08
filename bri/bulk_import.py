from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import *
import csv

def bulk_import_students(request):
    """Import students from CSV file with missing data tracking"""
    if request.method == 'POST':
        import csv
        
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, 'Please select a file.')
            return redirect('studentss')
        
        try:
            decoded_file = excel_file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)
            next(reader)  # Skip header
            
            success_count = 0
            error_count = 0
            students_with_missing_data = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Pad row with empty strings if missing fields
                    while len(row) < 15:
                        row.append('')
                    
                    first_name, last_name, username, password, roll_no, class_name, section_name, gender, dob, guardian_name, contact1, contact2, address, discount, bform = row
                    
                    # Track original data for missing field detection
                    original_data = {'guardian_name': guardian_name, 'contact1': contact1, 'contact2': contact2, 'address': address, 'dob': dob}
                    
                    # Set defaults for missing required fields
                    if not first_name: first_name = f'Student{row_num}'
                    if not last_name: last_name = 'Unknown'
                    if not username: username = f'student{row_num}'
                    if not password: password = 'password123'
                    if not roll_no: roll_no = row_num
                    if not gender: gender = 'Not Specified'
                    if not dob: dob = '2000-01-01'
                    
                    # Validate B-Form format if provided
                    if bform and bform.strip():
                        import re
                        if not re.match(r'^[0-9]{5}-[0-9]{7}-[0-9]{1}$', bform.strip()):
                            error_count += 1
                            continue
                    
                    std_class = Class.objects.get(class_name=class_name)
                    std_section = Section.objects.get(std_section=section_name, class_name=std_class)
                    
                    if Student.objects.filter(std_class=std_class, std_roll=roll_no).exists():
                        error_count += 1
                        continue
                    
                    # Handle duplicate username
                    original_username = username
                    counter = 1
                    while Username.objects.filter(username=username).exists():
                        username = f'{original_username}{counter}'
                        counter += 1
                    
                    new_username = Username.objects.create(username=username, password=make_password(password), role='student')
                    
                    Student.objects.create(
                        std_fname=first_name,
                        std_lname=last_name,
                        std_roll=roll_no,
                        std_class=std_class,
                        std_section=std_section,
                        gender=gender,
                        std_dob=dob,
                        guardian_name=guardian_name,
                        guardian_contact1=contact1,
                        guardian_contact2=contact2,
                        address=address,
                        discount_amount=float(discount) if discount else 0,
                        bform=bform,
                        username=new_username
                    )
                    success_count += 1
                    
                    # Track missing fields
                    missing_fields = []
                    if not original_data['guardian_name']: missing_fields.append('Guardian Name')
                    if not original_data['contact1'] and not original_data['contact2']: missing_fields.append('Guardian Contact')
                    if not original_data['address']: missing_fields.append('Address')
                    if not original_data['dob']: missing_fields.append('Date of Birth')
                    
                    if missing_fields:
                        students_with_missing_data.append({'name': f'{first_name} {last_name}', 'roll': roll_no, 'class': class_name, 'section': section_name, 'missing_fields': missing_fields})
                    
                except Exception as e:
                    error_count += 1
                    continue
            
            if success_count > 0:
                messages.success(request, f'{success_count} students imported successfully!')
            if error_count > 0:
                messages.warning(request, f'{error_count} rows had errors and were skipped.')
            
            # Store missing data in session for display
            if students_with_missing_data:
                request.session['students_with_missing_data'] = students_with_missing_data
                messages.info(request, f"{len(students_with_missing_data)} students imported with missing data. Check the Missing Data Report below.")
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
    
    return redirect('studentss')