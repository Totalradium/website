from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages
from .models import Student, Attendance, Class, Section
from .views import admin_required
import json
from django.utils import timezone
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64

@admin_required
def barcode_attendance(request):
    """Barcode attendance marking"""
    if request.method == 'POST':
        data = json.loads(request.body)
        roll_number = data.get('roll_number')
        status = data.get('status', 'Present')
        
        try:
            student = Student.objects.get(std_roll=roll_number, is_active=True)
            
            # Mark attendance
            today = timezone.now().date()
            attendance, created = Attendance.objects.update_or_create(
                student=student,
                date=today,
                defaults={'status': 'P' if status == 'Present' else 'A'}
            )
            
            # Get fee status
            from django.utils import timezone
            current_month = timezone.now().strftime('%Y-%m')
            fee_status = 'No Fee'
            try:
                from .models import StudentFee
                student_fee = StudentFee.objects.filter(
                    student=student,
                    month=current_month
                ).first()
                if student_fee:
                    fee_status = 'Paid' if student_fee.is_paid else 'Unpaid'
            except:
                pass
            
            return JsonResponse({
                'success': True,
                'student': {
                    'name': f'{student.std_fname} {student.std_lname}',
                    'roll': student.std_roll,
                    'class': student.std_class.class_name,
                    'section': student.std_section.std_section if student.std_section else 'N/A',
                    'image': student.profile_picture.url if student.profile_picture else None,
                    'fee_status': fee_status
                }
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': f'Student with roll number {roll_number} not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'barcode_attendance.html')

@admin_required
def print_student_cards(request):
    """Print student ID cards with barcodes"""
    classes = Class.objects.all()
    sections = Section.objects.all()
    students = []
    
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    
    students = Student.objects.filter(is_active=True)
    
    if class_id:
        students = students.filter(std_class_id=class_id)
    if section_id and section_id != 'all':
        students = students.filter(std_section_id=section_id)
        
    students = students.order_by('std_class__class_name', 'std_section__std_section', 'std_roll')
    
    # Generate barcodes for each student
    for student in students:
            barcode_value = f"{student.std_roll:04d}"
            code39 = barcode.get_barcode_class('code39')
            barcode_instance = code39(barcode_value, writer=ImageWriter())
            buffer = BytesIO()
            barcode_instance.write(buffer)
            student.barcode_data = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'print_student_cards.html', {
        'classes': classes,
        'sections': sections,
        'students': students,
        'selected_class_id': class_id,
        'selected_section_id': section_id
    })