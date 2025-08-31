from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from .models import Student, Exam, Marksheet
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import os
import threading
import json

def generate_exam_report_pdf(student, exam_results):
    """Generate PDF report for a student"""
    try:
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join('media', 'exam_reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Create PDF filename
        filename = f"{student.std_fname}_{student.std_lname}_exam_report.pdf"
        filepath = os.path.join(reports_dir, filename)
        
        # Create PDF
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "BRIGHTWAY FOUNDATION SCHOOL")
        c.drawString(50, height - 70, "EXAMINATION REPORT")
        
        # Student Info
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 110, f"Student Name: {student.std_fname} {student.std_lname}")
        c.drawString(50, height - 130, f"Class: {student.std_class.class_name}")
        c.drawString(50, height - 150, f"Section: {student.std_section.std_section if student.std_section else 'N/A'}")
        c.drawString(50, height - 170, f"Roll Number: {student.std_roll}")
        
        # Results Table Header
        y_position = height - 220
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, "Subject")
        c.drawString(200, y_position, "Obtained Marks")
        c.drawString(350, y_position, "Total Marks")
        c.drawString(450, y_position, "Percentage")
        
        # Draw line under header
        c.line(50, y_position - 5, 550, y_position - 5)
        
        # Results Data
        c.setFont("Helvetica", 10)
        y_position -= 25
        total_obtained = 0
        total_marks = 0
        
        for result in exam_results:
            exam = result.exam
            obtained = result.marks
            total = exam.total_marks
            percentage = (obtained / total * 100) if total > 0 else 0
            
            c.drawString(50, y_position, exam.name)
            c.drawString(200, y_position, str(obtained))
            c.drawString(350, y_position, str(total))
            c.drawString(450, y_position, f"{percentage:.1f}%")
            
            total_obtained += obtained
            total_marks += total
            y_position -= 20
        
        # Overall Result
        overall_percentage = (total_obtained / total_marks * 100) if total_marks > 0 else 0
        c.line(50, y_position - 5, 550, y_position - 5)
        y_position -= 20
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, "OVERALL RESULT")
        c.drawString(200, y_position, str(total_obtained))
        c.drawString(350, y_position, str(total_marks))
        c.drawString(450, y_position, f"{overall_percentage:.1f}%")
        
        # Grade
        if overall_percentage >= 90:
            grade = "A+"
        elif overall_percentage >= 80:
            grade = "A"
        elif overall_percentage >= 70:
            grade = "B"
        elif overall_percentage >= 60:
            grade = "C"
        elif overall_percentage >= 50:
            grade = "D"
        else:
            grade = "F"
        
        c.drawString(50, y_position - 30, f"Grade: {grade}")
        
        # Footer
        c.setFont("Helvetica", 10)
        c.drawString(50, 50, f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.save()
        return filepath
        
    except Exception as e:
        print(f"Error generating PDF for {student}: {e}")
        return None

def exam_reports_view(request):
    """View for exam reports management"""
    exams = Exam.objects.all().order_by('-date')
    classes = Class.objects.all()
    
    return render(request, 'exam_reports.html', {
        'exams': exams,
        'classes': classes
    })

def generate_and_send_reports(request):
    """Generate and send exam reports via WhatsApp"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            exam_ids = data.get('exam_ids', [])
            class_id = data.get('class_id')
            section_id = data.get('section_id')
            
            # Get students
            students_query = Student.objects.filter(is_active=True)
            if class_id:
                students_query = students_query.filter(std_class_id=class_id)
            if section_id:
                students_query = students_query.filter(std_section_id=section_id)
            
            students = students_query.select_related('std_class', 'std_section')
            
            def generate_and_send():
                from whatsapp_automation import WhatsAppBot
                
                bot = WhatsAppBot()
                try:
                    if not bot.is_logged_in():
                        bot.wait_for_qr_scan()
                    
                    reports_to_send = {}
                    
                    for student in students:
                        # Get exam results for this student
                        exam_results = Marksheet.objects.filter(
                            student=student,
                            exam_id__in=exam_ids
                        ).select_related('exam')
                        
                        if exam_results.exists():
                            # Generate PDF report
                            pdf_path = generate_exam_report_pdf(student, exam_results)
                            
                            if pdf_path:
                                # Get guardian phone
                                phone = student.guardian_contact1 or student.guardian_contact2
                                if phone:
                                    if hasattr(phone, 'as_e164'):
                                        phone_str = phone.as_e164
                                    else:
                                        phone_str = str(phone)
                                    
                                    reports_to_send[phone_str] = {
                                        'path': pdf_path,
                                        'caption': f"Exam Report for {student.std_fname} {student.std_lname}"
                                    }
                    
                    # Send all reports
                    if reports_to_send:
                        bot.send_bulk_files(reports_to_send)
                    
                finally:
                    bot.close()
            
            # Start in background thread
            thread = threading.Thread(target=generate_and_send)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({
                'success': True, 
                'message': f'Generating and sending reports for {students.count()} students...'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def get_exam_students(request):
    """Get students for selected exams"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            exam_ids = data.get('exam_ids', [])
            
            # Get students who have results for these exams
            students_with_results = Marksheet.objects.filter(
                exam_id__in=exam_ids
            ).values_list('student_id', flat=True).distinct()
            
            students = Student.objects.filter(
                id__in=students_with_results,
                is_active=True
            ).select_related('std_class', 'std_section')
            
            student_list = []
            for student in students:
                phone = student.guardian_contact1 or student.guardian_contact2
                student_list.append({
                    'id': student.id,
                    'name': f"{student.std_fname} {student.std_lname}",
                    'class': student.std_class.class_name,
                    'section': student.std_section.std_section if student.std_section else 'N/A',
                    'phone': str(phone) if phone else 'No Phone'
                })
            
            return JsonResponse({
                'students': student_list,
                'count': len(student_list)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})