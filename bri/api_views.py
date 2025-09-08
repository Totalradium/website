import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Student, Class, Section, Attendance, Fee, StudentFee
try:
    from .models import Teacher, TestSession, Test, Subject
except ImportError:
    Teacher = TestSession = Test = Subject = None
from datetime import datetime

def authenticate_api_request(request):
    """Check if request has valid API key"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    
    api_key = auth_header.replace('Bearer ', '')
    expected_key = getattr(settings, 'SYNC_API_KEY', 'your-secret-key')
    
    return api_key == expected_key

@csrf_exempt
@require_http_methods(["POST"])
def sync_students_api(request):
    """API endpoint to receive student data from local app"""
    if not authenticate_api_request(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # Sync classes first
        classes_data = data.get('classes', [])
        for cls_data in classes_data:
            Class.objects.update_or_create(
                id=cls_data['id'],
                defaults={
                    'class_name': cls_data['class_name'],
                    'class_order': cls_data.get('class_order', 0)
                }
            )
        
        # Sync sections
        sections_data = data.get('sections', [])
        for section_data in sections_data:
            if section_data['class_name_id']:
                try:
                    class_obj = Class.objects.get(id=section_data['class_name_id'])
                    Section.objects.update_or_create(
                        id=section_data['id'],
                        defaults={
                            'std_section': section_data['std_section'],
                            'class_name': class_obj
                        }
                    )
                except Class.DoesNotExist:
                    continue
        
        # Sync students
        students_data = data.get('students', [])
        synced_count = 0
        
        for student_data in students_data:
            try:
                # Get related objects
                std_class = None
                if student_data['std_class_id']:
                    try:
                        std_class = Class.objects.get(id=student_data['std_class_id'])
                    except Class.DoesNotExist:
                        pass
                
                std_section = None
                if student_data['std_section_id']:
                    try:
                        std_section = Section.objects.get(id=student_data['std_section_id'])
                    except Section.DoesNotExist:
                        pass
                
                # Parse date
                std_dob = None
                if student_data['std_dob']:
                    std_dob = datetime.fromisoformat(student_data['std_dob']).date()
                
                # Create or update student
                Student.objects.update_or_create(
                    id=student_data['id'],
                    defaults={
                        'std_fname': student_data['std_fname'],
                        'std_lname': student_data['std_lname'],
                        'std_roll': student_data['std_roll'],
                        'std_dob': std_dob,
                        'gender': student_data['gender'],
                        'std_class': std_class,
                        'std_section': std_section,
                        'guardian_name': student_data['guardian_name'],
                        'guardian_contact1': student_data['guardian_contact1'],
                        'guardian_contact2': student_data['guardian_contact2'],
                        'address': student_data['address'],
                        'discount_amount': student_data['discount_amount']
                    }
                )
                synced_count += 1
                
            except Exception as e:
                print(f"Error syncing student {student_data.get('id')}: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Synced {synced_count} students successfully',
            'synced_count': synced_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def sync_attendance_api(request):
    """API endpoint to receive attendance data from local app"""
    if not authenticate_api_request(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        attendance_data = data.get('attendance', [])
        synced_count = 0
        
        for att_data in attendance_data:
            try:
                # Get student
                student = Student.objects.get(id=att_data['student_id'])
                
                # Parse dates
                attendance_date = datetime.fromisoformat(att_data['attendance_date']).date()
                marked_time = None
                if att_data['marked_time']:
                    marked_time = datetime.fromisoformat(att_data['marked_time'])
                
                # Create or update attendance
                Attendance.objects.update_or_create(
                    id=att_data['id'],
                    defaults={
                        'student': student,
                        'attendance_date': attendance_date,
                        'status': att_data['status'],
                        'marked_time': marked_time
                    }
                )
                synced_count += 1
                
            except Student.DoesNotExist:
                print(f"Student not found for attendance {att_data.get('id')}")
                continue
            except Exception as e:
                print(f"Error syncing attendance {att_data.get('id')}: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Synced {synced_count} attendance records successfully',
            'synced_count': synced_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def sync_fees_api(request):
    """API endpoint to receive fee data from local app"""
    if not authenticate_api_request(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # Sync fees first
        fees_data = data.get('fees', [])
        for fee_data in fees_data:
            try:
                # Get related objects
                class_obj = None
                if fee_data['class_name_id']:
                    try:
                        class_obj = Class.objects.get(id=fee_data['class_name_id'])
                    except Class.DoesNotExist:
                        pass
                
                section_obj = None
                if fee_data['section_id']:
                    try:
                        section_obj = Section.objects.get(id=fee_data['section_id'])
                    except Section.DoesNotExist:
                        pass
                
                # Parse date
                created_at = None
                if fee_data['created_at']:
                    created_at = datetime.fromisoformat(fee_data['created_at'])
                
                Fee.objects.update_or_create(
                    id=fee_data['id'],
                    defaults={
                        'class_name': class_obj,
                        'section': section_obj,
                        'amount': fee_data['amount'],
                        'description': fee_data['description']
                    }
                )
                
            except Exception as e:
                print(f"Error syncing fee {fee_data.get('id')}: {e}")
                continue
        
        # Sync student fees
        student_fees_data = data.get('student_fees', [])
        synced_count = 0
        
        for sf_data in student_fees_data:
            try:
                # Get related objects
                student = Student.objects.get(id=sf_data['student_id'])
                fee = Fee.objects.get(id=sf_data['fee_id'])
                
                # Parse dates
                due_date = None
                if sf_data['due_date']:
                    due_date = datetime.fromisoformat(sf_data['due_date']).date()
                
                payment_date = None
                if sf_data['payment_date']:
                    payment_date = datetime.fromisoformat(sf_data['payment_date']).date()
                
                StudentFee.objects.update_or_create(
                    id=sf_data['id'],
                    defaults={
                        'student': student,
                        'fee': fee,
                        'month': sf_data['month'],
                        'amount_due': sf_data['amount_due'],
                        'amount_paid': sf_data['amount_paid'],
                        'is_paid': sf_data['is_paid'],
                        'due_date': due_date,
                        'payment_date': payment_date
                    }
                )
                synced_count += 1
                
            except (Student.DoesNotExist, Fee.DoesNotExist):
                print(f"Related objects not found for student fee {sf_data.get('id')}")
                continue
            except Exception as e:
                print(f"Error syncing student fee {sf_data.get('id')}: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Synced {len(fees_data)} fees and {synced_count} student fee records',
            'synced_count': synced_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for connection testing"""
    if not authenticate_api_request(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    return JsonResponse({
        'status': 'healthy',
        'message': 'API is working correctly',
        'timestamp': datetime.now().isoformat()
    })

@csrf_exempt
@require_http_methods(["POST"])
def sync_teachers_api(request):
    """API endpoint to receive teacher data from local app"""
    if not authenticate_api_request(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        teachers_data = data.get('teachers', [])
        synced_count = 0
        
        for teacher_data in teachers_data:
            try:
                Teacher.objects.update_or_create(
                    id=teacher_data['id'],
                    defaults={
                        'teacher_fname': teacher_data['teacher_fname'],
                        'teacher_lname': teacher_data['teacher_lname'],
                        'teacher_contact': teacher_data['teacher_contact'],
                        'teacher_email': teacher_data['teacher_email'],
                        'teacher_address': teacher_data['teacher_address'],
                        'teacher_qualification': teacher_data['teacher_qualification'],
                        'teacher_experience': teacher_data['teacher_experience'],
                        'teacher_salary': teacher_data['teacher_salary']
                    }
                )
                synced_count += 1
                
            except Exception as e:
                print(f"Error syncing teacher {teacher_data.get('id')}: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Synced {synced_count} teachers successfully',
            'synced_count': synced_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def sync_exams_api(request):
    """API endpoint to receive exam data from local app"""
    if not authenticate_api_request(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # Sync subjects first
        subjects_data = data.get('subjects', [])
        for subject_data in subjects_data:
            try:
                class_obj = None
                if subject_data['class_name_id']:
                    try:
                        class_obj = Class.objects.get(id=subject_data['class_name_id'])
                    except Class.DoesNotExist:
                        pass
                
                Subject.objects.update_or_create(
                    id=subject_data['id'],
                    defaults={
                        'subject_name': subject_data['subject_name'],
                        'class_name': class_obj
                    }
                )
                
            except Exception as e:
                print(f"Error syncing subject {subject_data.get('id')}: {e}")
                continue
        
        # Sync test sessions
        sessions_data = data.get('test_sessions', [])
        for session_data in sessions_data:
            try:
                class_obj = None
                if session_data['class_name_id']:
                    try:
                        class_obj = Class.objects.get(id=session_data['class_name_id'])
                    except Class.DoesNotExist:
                        pass
                
                section_obj = None
                if session_data['section_id']:
                    try:
                        section_obj = Section.objects.get(id=session_data['section_id'])
                    except Section.DoesNotExist:
                        pass
                
                TestSession.objects.update_or_create(
                    id=session_data['id'],
                    defaults={
                        'name': session_data['name'],
                        'class_name': class_obj,
                        'section': section_obj,
                        'month': session_data['month'],
                        'is_active': session_data['is_active']
                    }
                )
                
            except Exception as e:
                print(f"Error syncing test session {session_data.get('id')}: {e}")
                continue
        
        # Sync tests
        tests_data = data.get('tests', [])
        synced_count = 0
        for test_data in tests_data:
            try:
                test_session = None
                if test_data['test_session_id']:
                    try:
                        test_session = TestSession.objects.get(id=test_data['test_session_id'])
                    except TestSession.DoesNotExist:
                        pass
                
                subject = None
                if test_data['subject_id']:
                    try:
                        subject = Subject.objects.get(id=test_data['subject_id'])
                    except Subject.DoesNotExist:
                        pass
                
                test_date = None
                if test_data['test_date']:
                    test_date = datetime.fromisoformat(test_data['test_date']).date()
                
                Test.objects.update_or_create(
                    id=test_data['id'],
                    defaults={
                        'test_session': test_session,
                        'subject': subject,
                        'total_marks': test_data['total_marks'],
                        'test_date': test_date
                    }
                )
                synced_count += 1
                
            except Exception as e:
                print(f"Error syncing test {test_data.get('id')}: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Synced {len(subjects_data)} subjects, {len(sessions_data)} sessions, {synced_count} tests',
            'synced_count': synced_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)