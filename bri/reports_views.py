from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import *
from functools import wraps
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from io import BytesIO
from datetime import datetime, date
from django.db.models import Q

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id') or request.session.get('user_role') != 'admin':
            messages.error(request, 'Admin access required.')
            return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@admin_required
def reports_dashboard(request):
    """Main reports dashboard"""
    try:
        return render(request, 'reports/reports_dashboard.html')
    except Exception as e:
        messages.error(request, f'Error loading reports dashboard: {str(e)}')
        return redirect('admin_dashboard')

@admin_required
def student_reports(request):
    """Student reports with filters"""
    try:
        classes = Class.objects.all()
        sections = Section.objects.all()
        students = []
    except Exception as e:
        messages.error(request, f'Error loading student reports: {str(e)}')
        return redirect('reports_dashboard')
    
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        section_id = request.POST.get('section_id')
        format_type = request.POST.get('format')
        
        students = Student.objects.filter(is_active=True)
        if class_id:
            students = students.filter(std_class_id=class_id)
        if section_id:
            students = students.filter(std_section_id=section_id)
        
        if format_type == 'csv':
            return export_students_csv(students)
        elif format_type == 'pdf':
            return export_students_pdf(students)
    
    return render(request, 'reports/student_reports.html', {
        'classes': classes,
        'sections': sections
    })

@admin_required
def exam_reports(request):
    """Exam reports with filters"""
    sessions = TestSession.objects.all()
    
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        format_type = request.POST.get('format')
        
        if session_id:
            session = TestSession.objects.get(id=session_id)
            results = StudentTestResult.objects.filter(test__session=session)
            
            if format_type == 'csv':
                return export_exam_csv(session, results)
            elif format_type == 'pdf':
                return export_exam_pdf(session, results)
    
    return render(request, 'reports/exam_reports.html', {
        'sessions': sessions
    })

@admin_required
def fee_reports_export(request):
    """Fee reports with filters"""
    classes = Class.objects.all()
    
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        month = request.POST.get('month')
        status = request.POST.get('status')
        format_type = request.POST.get('format')
        
        fees = StudentFee.objects.all()
        if class_id:
            fees = fees.filter(fee__class_name_id=class_id)
        if month:
            fees = fees.filter(month=month)
        if status == 'paid':
            fees = fees.filter(is_paid=True)
        elif status == 'unpaid':
            fees = fees.filter(is_paid=False)
        
        if format_type == 'csv':
            return export_fees_csv(fees)
        elif format_type == 'pdf':
            return export_fees_pdf(fees)
    
    return render(request, 'reports/fee_reports.html', {
        'classes': classes
    })

@admin_required
def user_reports(request):
    """User reports with activity logs"""
    users = Username.objects.all()
    
    if request.method == 'POST':
        format_type = request.POST.get('format')
        
        if format_type == 'csv':
            return export_users_csv(users)
        elif format_type == 'pdf':
            return export_users_pdf(users)
    
    return render(request, 'reports/user_reports.html', {
        'users': users
    })

@admin_required
def activity_logs(request):
    """User activity logs"""
    logs = UserActivityLog.objects.all().order_by('-timestamp')
    filtered_logs = None
    
    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        user_id = request.POST.get('user_id')
        format_type = request.POST.get('format')
        action = request.POST.get('action')
        
        # Apply filters
        filtered_logs = logs
        if from_date:
            filtered_logs = filtered_logs.filter(timestamp__date__gte=from_date)
        if to_date:
            filtered_logs = filtered_logs.filter(timestamp__date__lte=to_date)
        if user_id:
            filtered_logs = filtered_logs.filter(user_id=user_id)
        
        # Handle different actions
        if action == 'download':
            if format_type == 'csv':
                return export_logs_csv(filtered_logs)
            elif format_type == 'pdf':
                return export_logs_pdf(filtered_logs)
        elif action == 'view':
            # Return filtered results to display in table
            pass
    
    users = Username.objects.all()
    return render(request, 'reports/activity_logs.html', {
        'logs': logs[:100],  # Show first 100 logs by default
        'filtered_logs': filtered_logs,  # Show filtered logs when viewing
        'users': users
    })

# Export functions
def export_students_csv(students):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="students_report_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Roll No', 'Class', 'Section', 'Guardian', 'Phone', 'Status'])
    
    for student in students:
        writer.writerow([
            f"{student.std_fname} {student.std_lname}",
            student.std_roll,
            student.std_class.class_name,
            student.std_section.std_section if student.std_section else 'N/A',
            student.guardian_name,
            student.guardian_contact1 or 'N/A',
            'Active' if student.is_active else 'Inactive'
        ])
    
    return response

def export_students_pdf(students):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Students Report")
    
    p.setFont("Helvetica", 10)
    y = height - 100
    
    for student in students:
        if y < 50:
            p.showPage()
            y = height - 50
        
        text = f"{student.std_fname} {student.std_lname} - Roll: {student.std_roll} - Class: {student.std_class.class_name}"
        p.drawString(50, y, text)
        y -= 20
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="students_report_{date.today()}.pdf"'
    return response

def export_exam_csv(session, results):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="exam_report_{session.name}_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Subject', 'Test', 'Total Marks', 'Obtained Marks', 'Percentage'])
    
    for result in results:
        percentage = (result.obtained_marks / result.test.total_marks * 100) if result.test.total_marks > 0 else 0
        writer.writerow([
            f"{result.student.std_fname} {result.student.std_lname}",
            result.test.subject,
            result.test.test_name,
            result.test.total_marks,
            result.obtained_marks,
            f"{percentage:.1f}%"
        ])
    
    return response

def export_exam_pdf(session, results):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Exam Report - {session.name}")
    
    p.setFont("Helvetica", 8)
    y = height - 100
    
    for result in results:
        if y < 50:
            p.showPage()
            y = height - 50
        
        percentage = (result.obtained_marks / result.test.total_marks * 100) if result.test.total_marks > 0 else 0
        text = f"{result.student.std_fname} {result.student.std_lname} - {result.test.subject} - {result.obtained_marks}/{result.test.total_marks} ({percentage:.1f}%)"
        p.drawString(50, y, text)
        y -= 15
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="exam_report_{session.name}_{date.today()}.pdf"'
    return response

def export_fees_csv(fees):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="fee_report_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Class', 'Month', 'Amount Due', 'Amount Paid', 'Status', 'Due Date'])
    
    for fee in fees:
        writer.writerow([
            f"{fee.student.std_fname} {fee.student.std_lname}",
            f"{fee.fee.class_name.class_name}-{fee.fee.section.std_section}",
            fee.month,
            fee.amount_due,
            fee.amount_paid,
            'Paid' if fee.is_paid else 'Unpaid',
            fee.due_date
        ])
    
    return response

def export_fees_pdf(fees):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Fee Report")
    
    p.setFont("Helvetica", 8)
    y = height - 100
    
    for fee in fees:
        if y < 50:
            p.showPage()
            y = height - 50
        
        text = f"{fee.student.std_fname} {fee.student.std_lname} - {fee.month} - PKR {fee.amount_due} - {'Paid' if fee.is_paid else 'Unpaid'}"
        p.drawString(50, y, text)
        y -= 15
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="fee_report_{date.today()}.pdf"'
    return response

def export_users_csv(users):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="users_report_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Username', 'Full Name', 'Role', 'Created Date'])
    
    for user in users:
        writer.writerow([
            user.username,
            user.full_name or 'N/A',
            user.get_role_display(),
            'N/A'  # Add created date if available
        ])
    
    return response

def export_users_pdf(users):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Users Report")
    
    p.setFont("Helvetica", 10)
    y = height - 100
    
    for user in users:
        if y < 50:
            p.showPage()
            y = height - 50
        
        text = f"{user.username} - {user.full_name or 'N/A'} - {user.get_role_display()}"
        p.drawString(50, y, text)
        y -= 20
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="users_report_{date.today()}.pdf"'
    return response

def export_logs_csv(logs):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="activity_logs_{date.today()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['User', 'Action', 'Model', 'Description', 'IP Address', 'Timestamp'])
    
    for log in logs:
        writer.writerow([
            log.user.username,
            log.get_action_type_display(),
            log.model_name,
            log.description,
            log.ip_address or 'N/A',
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

def export_logs_pdf(logs):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Activity Logs Report")
    
    p.setFont("Helvetica", 8)
    y = height - 100
    
    for log in logs:
        if y < 50:
            p.showPage()
            y = height - 50
        
        text = f"{log.timestamp.strftime('%Y-%m-%d %H:%M')} - {log.user.username} - {log.get_action_type_display()} - {log.description[:50]}"
        p.drawString(50, y, text)
        y -= 15
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="activity_logs_{date.today()}.pdf"'
    return response