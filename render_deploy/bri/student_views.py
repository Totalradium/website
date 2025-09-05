from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import Student, Attendance, StudentFee, Test
from datetime import datetime, timedelta
import json

def student_login(request):
    """Student login page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            # Find student by username
            student = Student.objects.get(username=username)
            
            # Check password (assuming you have a password field)
            if hasattr(student, 'password') and student.password == password:
                # Store student info in session
                request.session['student_id'] = student.id
                request.session['student_name'] = f"{student.std_fname} {student.std_lname}"
                return redirect('student_dashboard')
            else:
                messages.error(request, 'Invalid username or password')
        except Student.DoesNotExist:
            messages.error(request, 'Student not found')
    
    return render(request, 'student_login.html')

def student_logout(request):
    """Student logout"""
    request.session.flush()
    return redirect('student_login')

def student_dashboard(request):
    """Student dashboard"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Get recent attendance
    recent_attendance = Attendance.objects.filter(
        student=student
    ).order_by('-attendance_date')[:10]
    
    # Get fee status
    unpaid_fees = StudentFee.objects.filter(
        student=student,
        is_paid=False
    )
    
    # Get recent test results
    recent_tests = []
    try:
        recent_tests = Test.objects.filter(
            test_session__class_name=student.std_class,
            test_session__section=student.std_section
        ).order_by('-test_date')[:5]
    except:
        pass
    
    context = {
        'student': student,
        'recent_attendance': recent_attendance,
        'unpaid_fees': unpaid_fees,
        'recent_tests': recent_tests
    }
    return render(request, 'student_dashboard.html', context)

def student_attendance(request):
    """Student attendance history"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Get attendance for current month
    current_month = datetime.now().replace(day=1)
    attendance_records = Attendance.objects.filter(
        student=student,
        attendance_date__gte=current_month
    ).order_by('-attendance_date')
    
    # Calculate statistics
    total_days = attendance_records.count()
    present_days = attendance_records.filter(status='Present').count()
    absent_days = attendance_records.filter(status='Absent').count()
    
    context = {
        'student': student,
        'attendance_records': attendance_records,
        'total_days': total_days,
        'present_days': present_days,
        'absent_days': absent_days,
        'attendance_percentage': round((present_days / total_days * 100) if total_days > 0 else 0, 1)
    }
    return render(request, 'student_attendance.html', context)

def student_fees(request):
    """Student fee information"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Get all fee records
    fee_records = StudentFee.objects.filter(student=student).order_by('-month')
    
    # Calculate totals
    total_due = sum(fee.amount_due for fee in fee_records)
    total_paid = sum(fee.amount_paid for fee in fee_records)
    total_pending = total_due - total_paid
    
    context = {
        'student': student,
        'fee_records': fee_records,
        'total_due': total_due,
        'total_paid': total_paid,
        'total_pending': total_pending
    }
    return render(request, 'student_fees.html', context)

def student_results(request):
    """Student test results"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Get test sessions for student's class and section
    test_sessions = []
    try:
        from .models import TestSession
        test_sessions = TestSession.objects.filter(
            class_name=student.std_class,
            section=student.std_section
        ).order_by('-month')
    except:
        pass
    
    context = {
        'student': student,
        'test_sessions': test_sessions
    }
    return render(request, 'student_results.html', context)

def print_fee_voucher(request):
    """Print fee voucher for student"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Get unpaid fees
    unpaid_fees = StudentFee.objects.filter(
        student=student,
        is_paid=False
    )
    
    context = {
        'student': student,
        'unpaid_fees': unpaid_fees,
        'total_amount': sum(fee.amount_due - fee.amount_paid for fee in unpaid_fees),
        'print_date': datetime.now()
    }
    return render(request, 'fee_voucher.html', context)

def print_result_card(request, session_id=None):
    """Print result card for student"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Get test session and results
    test_session = None
    test_results = []
    
    try:
        from .models import TestSession, Test
        if session_id:
            test_session = get_object_or_404(TestSession, id=session_id)
            test_results = Test.objects.filter(test_session=test_session)
    except:
        pass
    
    context = {
        'student': student,
        'test_session': test_session,
        'test_results': test_results,
        'print_date': datetime.now()
    }
    return render(request, 'result_card.html', context)