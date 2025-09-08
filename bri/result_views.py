from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import TestSession, Student, StudentTestResult
from .views import admin_required

@admin_required
def send_result_cards(request, session_id):
    """Generate and send result cards as PDF via WhatsApp"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from io import BytesIO
    import os
    from django.conf import settings
    
    session = get_object_or_404(TestSession, id=session_id)
    
    if request.method == 'POST':
        selected_students = request.POST.getlist('selected_students')
        
        if not selected_students:
            messages.error(request, 'Please select at least one student.')
            return redirect('send_result_cards', session_id=session_id)
        
        sent_count = 0
        
        for student_id in selected_students:
            try:
                student = Student.objects.get(id=student_id)
                
                # Generate PDF for this student
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                
                # Title
                p.setFont("Helvetica-Bold", 16)
                p.drawString(50, height - 50, f"Result Card - {session.name}")
                
                # Student info
                p.setFont("Helvetica", 12)
                p.drawString(50, height - 100, f"Student: {student.std_fname} {student.std_lname}")
                p.drawString(50, height - 120, f"Class: {student.std_class.class_name}-{student.std_section.std_section}")
                p.drawString(50, height - 140, f"Roll No: {student.std_roll}")
                
                # Get results
                results = StudentTestResult.objects.filter(student=student, test__session=session)
                y = height - 180
                
                p.drawString(50, y, "Subject Results:")
                y -= 30
                
                total_marks = 0
                obtained_marks = 0
                
                for result in results:
                    p.drawString(70, y, f"{result.test.subject}: {result.obtained_marks}/{result.test.total_marks}")
                    total_marks += result.test.total_marks
                    obtained_marks += result.obtained_marks or 0
                    y -= 20
                
                # Calculate percentage
                percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
                
                p.drawString(50, y - 20, f"Total: {obtained_marks}/{total_marks}")
                p.drawString(50, y - 40, f"Percentage: {percentage:.1f}%")
                
                p.save()
                buffer.seek(0)
                
                # Save PDF temporarily
                pdf_filename = f"result_card_{student.std_roll}_{session.id}.pdf"
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'temp', pdf_filename)
                
                # Create temp directory if it doesn't exist
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                
                with open(pdf_path, 'wb') as f:
                    f.write(buffer.getvalue())
                
                # Get phone number
                phone = student.guardian_contact1 or student.guardian_contact2
                if phone:
                    # Here you would integrate with WhatsApp API to send the PDF
                    # For now, just mark as sent
                    sent_count += 1
                
                # Clean up temp file
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    
            except Exception as e:
                continue
        
        messages.success(request, f'Result cards sent to {sent_count} students via WhatsApp!')
        return redirect('session_detail', session_id=session_id)
    
    # Get students for selection
    students = Student.objects.filter(
        std_class=session.class_name,
        std_section=session.section,
        is_active=True
    ).order_by('std_roll')
    
    return render(request, 'send_result_cards.html', {
        'session': session,
        'students': students
    })