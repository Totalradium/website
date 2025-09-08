import json
import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
from .models import Student, Class, Section, Attendance, Fee, StudentFee
try:
    from .models import Teacher, TestSession, Test, Subject
except ImportError:
    Teacher = TestSession = Test = Subject = None
from django.core import serializers
from datetime import datetime

def sync_dashboard(request):
    """Dashboard for data synchronization"""
    return render(request, 'sync_dashboard.html')

@csrf_exempt
def sync_to_remote(request):
    """Sync local data to remote server"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sync_type = data.get('sync_type', 'all')
            
            # Get remote server URL from request or settings
            remote_url = data.get('remote_url') or getattr(settings, 'REMOTE_SERVER_URL', 'https://website-8luq.onrender.com')
            api_key = data.get('api_key') or getattr(settings, 'SYNC_API_KEY', '0226afc1d8d8b6139cf89afddeac0aec03d89a2269b4b0d28439a66a64bec5a0')
            
            result = {}
            
            if sync_type in ['all', 'students']:
                result['students'] = sync_students(remote_url, api_key)
            
            if sync_type in ['all', 'attendance']:
                result['attendance'] = sync_attendance(remote_url, api_key)
                
            if sync_type in ['all', 'fees']:
                result['fees'] = sync_fees(remote_url, api_key)
                
            if sync_type in ['all', 'teachers']:
                result['teachers'] = sync_teachers(remote_url, api_key)
                
            if sync_type in ['all', 'exams']:
                result['exams'] = sync_exams(remote_url, api_key)
            
            return JsonResponse({
                'success': True,
                'message': 'Sync completed successfully',
                'results': result
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'error': 'Invalid request method'})

def sync_students(remote_url, api_key):
    """Sync student data to remote server"""
    try:
        # Get all students
        students = Student.objects.all()
        classes = Class.objects.all()
        sections = Section.objects.all()
        
        # Batch size for large datasets
        BATCH_SIZE = 100
        
        # Convert to JSON
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'std_fname': student.std_fname,
                'std_lname': student.std_lname,
                'std_roll': student.std_roll,
                'std_dob': student.std_dob.isoformat() if student.std_dob else None,
                'gender': student.gender,
                'std_class_id': student.std_class.id if student.std_class else None,
                'std_section_id': student.std_section.id if student.std_section else None,
                'guardian_name': student.guardian_name,
                'guardian_contact1': student.guardian_contact1,
                'guardian_contact2': student.guardian_contact2,
                'address': student.address,
                'discount_amount': float(student.discount_amount) if student.discount_amount else 0,
            })
        
        classes_data = []
        for cls in classes:
            classes_data.append({
                'id': cls.id,
                'class_name': cls.class_name,
                'class_order': cls.class_order
            })
            
        sections_data = []
        for section in sections:
            sections_data.append({
                'id': section.id,
                'std_section': section.std_section,
                'class_name_id': section.class_name.id if section.class_name else None
            })
        
        # Send classes and sections first (small datasets)
        payload = {
            'classes': classes_data,
            'sections': sections_data,
            'students': []
        }
        
        response = requests.post(
            f"{remote_url}/api/sync/students/",
            json=payload,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=60
        )
        
        if response.status_code != 200:
            return {'status': 'error', 'message': response.text}
        
        # Send students in batches
        total_synced = 0
        for i in range(0, len(students_data), BATCH_SIZE):
            batch = students_data[i:i + BATCH_SIZE]
            
            batch_payload = {
                'students': batch,
                'classes': [],
                'sections': []
            }
            
            response = requests.post(
                f"{remote_url}/api/sync/students/",
                json=batch_payload,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            
            if response.status_code == 200:
                total_synced += len(batch)
            else:
                return {'status': 'error', 'message': f'Batch {i//BATCH_SIZE + 1} failed: {response.text}'}
        
        return {'status': 'success', 'count': total_synced}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def sync_attendance(remote_url, api_key):
    """Sync attendance data to remote server"""
    try:
        # Get recent attendance (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        attendance_records = Attendance.objects.filter(
            attendance_date__gte=thirty_days_ago
        )
        
        attendance_data = []
        for record in attendance_records:
            attendance_data.append({
                'id': record.id,
                'student_id': record.student.id,
                'attendance_date': record.attendance_date.isoformat(),
                'status': record.status,
                'marked_time': record.marked_time.isoformat() if record.marked_time else None
            })
        
        payload = {'attendance': attendance_data}
        
        response = requests.post(
            f"{remote_url}/api/sync/attendance/",
            json=payload,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=60
        )
        
        if response.status_code == 200:
            return {'status': 'success', 'count': len(attendance_data)}
        else:
            return {'status': 'error', 'message': response.text}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def sync_fees(remote_url, api_key):
    """Sync fee data to remote server"""
    try:
        fees = Fee.objects.all()
        student_fees = StudentFee.objects.all()
        
        # Batch size for large datasets
        BATCH_SIZE = 200
        
        fees_data = []
        for fee in fees:
            fees_data.append({
                'id': fee.id,
                'class_name_id': fee.class_name.id if fee.class_name else None,
                'section_id': fee.section.id if fee.section else None,
                'amount': float(fee.amount),
                'description': fee.description,
                'created_at': fee.created_at.isoformat() if hasattr(fee, 'created_at') else None
            })
        
        student_fees_data = []
        for sf in student_fees:
            student_fees_data.append({
                'id': sf.id,
                'student_id': sf.student.id,
                'fee_id': sf.fee.id,
                'month': sf.month,
                'amount_due': float(sf.amount_due),
                'amount_paid': float(sf.amount_paid),
                'is_paid': sf.is_paid,
                'due_date': sf.due_date.isoformat() if sf.due_date else None,
                'payment_date': sf.payment_date.isoformat() if sf.payment_date else None
            })
        
        # Send fees first (usually small dataset)
        fees_payload = {
            'fees': fees_data,
            'student_fees': []
        }
        
        response = requests.post(
            f"{remote_url}/api/sync/fees/",
            json=fees_payload,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=60
        )
        
        if response.status_code != 200:
            return {'status': 'error', 'message': response.text}
        
        # Send student fees in batches
        total_synced = len(fees_data)
        for i in range(0, len(student_fees_data), BATCH_SIZE):
            batch = student_fees_data[i:i + BATCH_SIZE]
            
            batch_payload = {
                'fees': [],
                'student_fees': batch
            }
            
            response = requests.post(
                f"{remote_url}/api/sync/fees/",
                json=batch_payload,
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
            
            if response.status_code == 200:
                total_synced += len(batch)
            else:
                return {'status': 'error', 'message': f'Student fees batch {i//BATCH_SIZE + 1} failed: {response.text}'}
        
        return {'status': 'success', 'count': total_synced}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def sync_teachers(remote_url, api_key):
    """Sync teacher data to remote server"""
    try:
        if Teacher is None:
            return {'status': 'error', 'message': 'Teacher model not found'}
        
        teachers = Teacher.objects.all()
        
        teachers_data = []
        for teacher in teachers:
            teachers_data.append({
                'id': teacher.id,
                'teacher_fname': teacher.teacher_fname,
                'teacher_lname': teacher.teacher_lname,
                'teacher_contact': teacher.teacher_contact,
                'teacher_email': teacher.teacher_email,
                'teacher_address': teacher.teacher_address,
                'teacher_qualification': teacher.teacher_qualification,
                'teacher_experience': teacher.teacher_experience,
                'teacher_salary': float(teacher.teacher_salary) if teacher.teacher_salary else 0,
                'is_active': getattr(teacher, 'is_active', True)
            })
        
        payload = {'teachers': teachers_data}
        
        response = requests.post(
            f"{remote_url}/api/sync/teachers/",
            json=payload,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30
        )
        
        if response.status_code == 200:
            return {'status': 'success', 'count': len(teachers_data)}
        else:
            return {'status': 'error', 'message': response.text}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def sync_exams(remote_url, api_key):
    """Sync exam/test data to remote server"""
    try:
        if any(model is None for model in [Subject, TestSession, Test]):
            return {'status': 'error', 'message': 'Exam models not found'}
        
        # Sync subjects first
        subjects = Subject.objects.all()
        subjects_data = []
        for subject in subjects:
            subjects_data.append({
                'id': subject.id,
                'subject_name': subject.subject_name,
                'class_name_id': subject.class_name.id if subject.class_name else None
            })
        
        # Sync test sessions
        test_sessions = TestSession.objects.all()
        sessions_data = []
        for session in test_sessions:
            sessions_data.append({
                'id': session.id,
                'name': session.name,
                'class_name_id': session.class_name.id if session.class_name else None,
                'section_id': session.section.id if session.section else None,
                'month': session.month,
                'session_type': getattr(session, 'session_type', 'monthly'),
                'is_active': session.is_active
            })
        
        # Sync tests
        tests = Test.objects.all()
        tests_data = []
        for test in tests:
            tests_data.append({
                'id': test.id,
                'test_session_id': test.test_session.id if test.test_session else None,
                'subject_id': test.subject.id if test.subject else None,
                'test_name': getattr(test, 'test_name', ''),
                'total_marks': test.total_marks,
                'test_date': test.test_date.isoformat() if test.test_date else None
            })
        
        payload = {
            'subjects': subjects_data,
            'test_sessions': sessions_data,
            'tests': tests_data
        }
        
        response = requests.post(
            f"{remote_url}/api/sync/exams/",
            json=payload,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30
        )
        
        if response.status_code == 200:
            return {'status': 'success', 'count': len(subjects_data) + len(sessions_data) + len(tests_data)}
        else:
            return {'status': 'error', 'message': response.text}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}