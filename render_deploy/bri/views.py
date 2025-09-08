from django.shortcuts import render
from django.http import JsonResponse
from .models import Student, Class, Section, Attendance, Fee, StudentFee, Teacher, TestSession, Test, Subject

def dashboard(request):
    """Main dashboard for online version"""
    context = {
        'total_students': Student.objects.count(),
        'total_teachers': Teacher.objects.count(),
        'total_classes': Class.objects.count(),
        'recent_attendance': Attendance.objects.order_by('-attendance_date')[:10]
    }
    return render(request, 'dashboard.html', context)

def students_list(request):
    """List all students"""
    students = Student.objects.select_related('std_class', 'std_section').all()
    context = {'students': students}
    return render(request, 'students_list.html', context)

def attendance_list(request):
    """List attendance records"""
    attendance = Attendance.objects.select_related('student').order_by('-attendance_date')[:100]
    context = {'attendance_records': attendance}
    return render(request, 'attendance_list.html', context)

def fees_list(request):
    """List fee records"""
    fees = StudentFee.objects.select_related('student', 'fee').all()
    context = {'fees': fees}
    return render(request, 'fees_list.html', context)

def teachers_list(request):
    """List all teachers"""
    teachers = Teacher.objects.all()
    context = {'teachers': teachers}
    return render(request, 'teachers_list.html', context)

def exams_list(request):
    """List exam/test records"""
    test_sessions = TestSession.objects.select_related('class_name', 'section').all()
    tests = Test.objects.select_related('test_session', 'subject').all()
    context = {
        'test_sessions': test_sessions,
        'tests': tests
    }
    return render(request, 'exams_list.html', context)