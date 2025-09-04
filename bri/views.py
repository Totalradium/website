from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from functools import wraps
from django.db.models import Q
from bri.models import *
from .models import Fee, StudentFee, FeePayment, WhatsappMessage, PromoteBatchForm, AttendanceNotification, TestSession, Test
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse
from .models import Student as StudentModel
from django.db.models import Q
from .forms import CreateUserForm, StudentTestResultForm
from django.db import IntegrityError
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.utils.timezone import now

# Helper function for logging user activities
def log_user_activity(request, action_type, model_name, object_id, description):
    try:
        user = Username.objects.get(id=request.session.get('user_id'))
        UserActivityLog.objects.create(
            user=user,
            action_type=action_type,
            model_name=model_name,
            object_id=str(object_id),
            description=description,
            ip_address=request.META.get('REMOTE_ADDR')
        )
    except:
        pass

# Decorator to require admin role
def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id') or request.session.get('user_role') != 'admin':
            return redirect('admin_dashboard')  # Use the correct view name from urls.py
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_dashboard(request):
    if request.method == "POST":
        input_username = request.POST.get("username")
        input_password = request.POST.get("password")
        try:
            user = Username.objects.get(username=input_username)
            if check_password(input_password, user.password):
                # store session
                request.session['logged_in'] = True
                request.session['user_id'] = user.id
                request.session['user_role'] = user.role

                # redirect by role
                if user.role == "admin":
                    print("Attempt login:", input_username)
                    # Store user info in session
                    request.session['user_name'] = user.full_name or user.username
                    request.session['user_picture'] = user.profile_picture.url if user.profile_picture else None
                    return redirect('studentss')
                elif user.role == "teacher":
                    # Check if teacher is active
                    try:
                        teacher = user.teacher_profile.first()
                        if not teacher or not teacher.is_active:
                            return render(request, "admin_dashboard.html", {
                                "error": "Your account has been disabled. Please contact administrator."
                            })
                        request.session['user_name'] = f"{teacher.teacher_fname} {teacher.teacher_lname}"
                        request.session['user_picture'] = teacher.profile_picture.url if teacher.profile_picture else None
                    except:
                        request.session['user_name'] = user.username
                        request.session['user_picture'] = None
                    return redirect("teacher_home")
                elif user.role == "student":
                    # Check if student is active
                    try:
                        student = user.students.first()
                        if not student or not student.is_active:
                            return render(request, "admin_dashboard.html", {
                                "error": "Your account has been disabled. Please contact administrator."
                            })
                    except:
                        pass
                    return redirect("student_home")
                else:
                    return render(request, "admin_dashboard.html", {
                        "error": "Unknown user role."
                    })
            else:
                return render(request, "admin_dashboard.html", {
                    "error": "Incorrect password."
                })
        except Username.DoesNotExist:
            return render(request, "admin_dashboard.html", {
                "error": "User not found."
            })
    return render(request, "admin_dashboard.html")


def attendance_dashboard(request):
    from django.utils import timezone
    from django.db.models import Count, Q
    
    today = timezone.now().date()
    
    # Get today's attendance statistics
    total_students = Student.objects.filter(is_active=True).count()
    
    today_attendance = Attendance.objects.filter(date=today)
    present_count = today_attendance.filter(status='P').count()
    absent_count = today_attendance.filter(status='A').count()
    not_marked_count = total_students - (present_count + absent_count)
    
    # Calculate attendance percentage
    if total_students > 0:
        attendance_percentage = round((present_count / total_students) * 100, 1)
    else:
        attendance_percentage = 0
    
    context = {
        'today_date': today,
        'total_students': total_students,
        'present_count': present_count,
        'absent_count': absent_count,
        'not_marked_count': not_marked_count,
        'attendance_percentage': attendance_percentage,
    }
    
    return render(request, 'attendance_dashboard.html', context)

def export_attendance(request):
    import csv
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from io import BytesIO
    from datetime import datetime
    
    classes = Class.objects.all()
    attendance_data = None
    
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        section_id = request.POST.get('section_id')
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        export_format = request.POST.get('format')
        
        # Build query
        attendance_query = Attendance.objects.select_related('student', 'student__std_class', 'student__std_section')
        
        if from_date and to_date:
            attendance_query = attendance_query.filter(date__range=[from_date, to_date])
        
        if class_id:
            attendance_query = attendance_query.filter(student__std_class_id=class_id)
        
        if section_id:
            attendance_query = attendance_query.filter(student__std_section_id=section_id)
        
        attendance_data = attendance_query.order_by('date', 'student__std_roll')
        
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="attendance_report_{from_date}_to_{to_date}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Date', 'Student Name', 'Class', 'Section', 'Roll No', 'Status', 'Time Marked'])
            
            for record in attendance_data:
                writer.writerow([
                    record.date.strftime('%Y-%m-%d'),
                    f"{record.student.std_fname} {record.student.std_lname}",
                    record.student.std_class.class_name,
                    record.student.std_section.std_section if record.student.std_section else 'N/A',
                    record.student.std_roll,
                    'Present' if record.status == 'P' else 'Absent',
                    record.time_marked.strftime('%H:%M:%S') if record.time_marked else 'N/A'
                ])
            
            return response
        
        elif export_format == 'pdf':
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            # Title
            p.setFont("Helvetica-Bold", 16)
            p.drawString(50, height - 50, f"Attendance Report ({from_date} to {to_date})")
            
            # Headers
            p.setFont("Helvetica-Bold", 10)
            y = height - 100
            p.drawString(50, y, "Date")
            p.drawString(120, y, "Student Name")
            p.drawString(250, y, "Class")
            p.drawString(300, y, "Section")
            p.drawString(350, y, "Roll")
            p.drawString(400, y, "Status")
            p.drawString(470, y, "Time")
            
            # Data
            p.setFont("Helvetica", 8)
            y -= 20
            
            for record in attendance_data:
                if y < 50:  # New page
                    p.showPage()
                    y = height - 50
                
                p.drawString(50, y, record.date.strftime('%Y-%m-%d'))
                p.drawString(120, y, f"{record.student.std_fname} {record.student.std_lname}"[:15])
                p.drawString(250, y, record.student.std_class.class_name)
                p.drawString(300, y, record.student.std_section.std_section if record.student.std_section else 'N/A')
                p.drawString(350, y, str(record.student.std_roll))
                p.drawString(400, y, 'Present' if record.status == 'P' else 'Absent')
                p.drawString(470, y, record.time_marked.strftime('%H:%M:%S') if record.time_marked else 'N/A')
                y -= 15
            
            p.save()
            buffer.seek(0)
            
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="attendance_report_{from_date}_to_{to_date}.pdf"'
            return response
        
        return render(request, 'export_attendance.html', {
            'classes': classes,
            'attendance_data': attendance_data,
            'selected_class_id': class_id,
            'from_date': from_date,
            'to_date': to_date
        })
    
    return render(request, 'export_attendance.html', {'classes': classes})

def whatsapp_integration(request):
    from django.utils import timezone
    import json
    
    classes = Class.objects.all()
    today_date = timezone.now().date()
    
    return render(request, 'whatsapp_integration.html', {
        'classes': classes,
        'today_date': today_date
    })

def get_students_with_attendance(request):
    if request.method == 'POST':
        try:
            from django.utils import timezone
            from datetime import datetime
            
            class_id = request.POST.get('class_id')
            section_id = request.POST.get('section_id')
            attendance_date = request.POST.get('attendance_date')
            message_type = request.POST.get('message_type')
        
            print(f"Received data: class_id={class_id}, section_id={section_id}, date={attendance_date}, type={message_type}")
            
            # Build student query
            students_query = Student.objects.filter(is_active=True)
        
            if class_id:
                students_query = students_query.filter(std_class_id=class_id)
            if section_id:
                students_query = students_query.filter(std_section_id=section_id)
            
            students = students_query.select_related('std_class', 'std_section')
        
            # Parse attendance date
            try:
                attendance_date_obj = datetime.strptime(attendance_date, '%Y-%m-%d').date()
            except:
                return JsonResponse({'error': 'Invalid date format'})
        
            print(f"Found {students.count()} students")
            for s in students[:3]:  # Print first 3 students for debugging
                print(f"Student: {s.std_fname} {s.std_lname}, Class: {s.std_class.class_name}, Section: {s.std_section}, Phone1: {s.guardian_contact1}, Phone2: {s.guardian_contact2}")
        
            # Get attendance for the date
            attendance_records = Attendance.objects.filter(
                date=attendance_date_obj,
                student__in=students
            ).values('student_id', 'status')
            
            print(f"Found {len(attendance_records)} attendance records")
            
            attendance_dict = {record['student_id']: record['status'] for record in attendance_records}
            
            result_students = []
            for student in students:
                status = attendance_dict.get(student.id)
                status_text = 'Present' if status == 'P' else 'Absent' if status == 'A' else 'Not Marked'
                
                # Handle PhoneNumberField - extract phone number safely
                phone = 'No Phone'
                try:
                    # Try guardian_contact1 first
                    if hasattr(student, 'guardian_contact1') and student.guardian_contact1:
                        if hasattr(student.guardian_contact1, 'as_e164'):
                            # PhoneNumberField object
                            phone = student.guardian_contact1.as_e164
                        else:
                            # String field
                            phone = str(student.guardian_contact1).strip()
                    # Try guardian_contact2 if first is empty
                    elif hasattr(student, 'guardian_contact2') and student.guardian_contact2:
                        if hasattr(student.guardian_contact2, 'as_e164'):
                            phone = student.guardian_contact2.as_e164
                        else:
                            phone = str(student.guardian_contact2).strip()
                    
                    # Clean and format if we got a phone number
                    if phone and phone != 'No Phone':
                        phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                        
                        # Ensure international format for WhatsApp
                        if phone.startswith('+92'):
                            pass  # Already correct
                        elif phone.startswith('92'):
                            phone = '+' + phone
                        elif phone.startswith('0'):
                            phone = '+92' + phone[1:]
                        elif len(phone) >= 10:
                            phone = '+92' + phone
                        else:
                            phone = 'Invalid Phone'
                except Exception as e:
                    print(f"Phone processing error for {student.std_fname}: {e}")
                    phone = 'No Phone'
                
                # Add all students with their status
                result_students.append({
                    'name': f"{student.std_fname} {student.std_lname}",
                    'phone': phone or 'No Phone',
                    'class': student.std_class.class_name,
                    'section': student.std_section.std_section if student.std_section else 'N/A',
                    'status': status_text,
                    'roll': student.std_roll
                })
            
            # Filter based on message type after loading all students
            if message_type == 'absent':
                result_students = [s for s in result_students if s['status'] == 'Absent']
            elif message_type == 'present':
                result_students = [s for s in result_students if s['status'] == 'Present']
            # 'all' shows everyone regardless of status
            
            print(f"Returning {len(result_students)} students")
            return JsonResponse({
                'students': result_students, 
                'total_count': len(result_students),
                'debug_info': {
                    'total_students_found': students.count(),
                    'filtered_count': len(result_students),
                    'message_type': message_type,
                    'attendance_records': len(attendance_records)
                }
            })
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'})

def get_students_with_fees(request):
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class_id')
            section_id = request.POST.get('section_id')
            fee_month = request.POST.get('fee_month')
            fee_status = request.POST.get('fee_status')
            
            # Build student query
            students_query = Student.objects.filter(is_active=True)
            
            if class_id:
                students_query = students_query.filter(std_class_id=class_id)
            if section_id:
                students_query = students_query.filter(std_section_id=section_id)
            
            students = students_query.select_related('std_class', 'std_section')
            
            result_students = []
            for student in students:
                # Get fee information for this student and month
                student_fee = StudentFee.objects.filter(
                    student=student,
                    month=fee_month
                ).first()
                
                # Determine if we should include this student
                include_student = False
                fee_amount = 0
                fee_paid_status = 'No Fee'
                
                if student_fee:
                    fee_amount = student_fee.amount_due
                    fee_paid_status = 'Paid' if student_fee.is_paid else 'Unpaid'
                    
                    if fee_status == 'unpaid' and not student_fee.is_paid:
                        include_student = True
                    elif fee_status == 'all':
                        include_student = True
                elif fee_status == 'all':
                    include_student = True
                
                if include_student:
                    # Handle phone number
                    phone = 'No Phone'
                    try:
                        if hasattr(student, 'guardian_contact1') and student.guardian_contact1:
                            if hasattr(student.guardian_contact1, 'as_e164'):
                                phone = student.guardian_contact1.as_e164
                            else:
                                phone = str(student.guardian_contact1).strip()
                        elif hasattr(student, 'guardian_contact2') and student.guardian_contact2:
                            if hasattr(student.guardian_contact2, 'as_e164'):
                                phone = student.guardian_contact2.as_e164
                            else:
                                phone = str(student.guardian_contact2).strip()
                        
                        # Clean and format phone number
                        if phone and phone != 'No Phone':
                            phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                            
                            if phone.startswith('+92'):
                                pass
                            elif phone.startswith('92'):
                                phone = '+' + phone
                            elif phone.startswith('0'):
                                phone = '+92' + phone[1:]
                            elif len(phone) >= 10:
                                phone = '+92' + phone
                            else:
                                phone = 'Invalid Phone'
                    except Exception as e:
                        phone = 'No Phone'
                    
                    result_students.append({
                        'name': f"{student.std_fname} {student.std_lname}",
                        'phone': phone or 'No Phone',
                        'class': student.std_class.class_name,
                        'section': student.std_section.std_section if student.std_section else 'N/A',
                        'roll': student.std_roll,
                        'amount': fee_amount,
                        'fee_status': fee_paid_status,
                        'month': fee_month
                    })
            
            return JsonResponse({
                'students': result_students,
                'total_count': len(result_students)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'})

# WhatsApp functions moved to whatsapp_views.py

def attendance_home(request):
    return render(request, 'attendance_home.html', {
        'classes': Class.objects.all(),
        'sections': Section.objects.all()
    })

from django.shortcuts import get_object_or_404

def attendance_view(request):
    # Handle both POST and GET requests
    class_id = request.POST.get('class_id') or request.GET.get('class_id')
    section_id = request.POST.get('section_id') or request.GET.get('section_id')
    
    if class_id and section_id:
        try:
            class_id = int(class_id)
            section_id = int(section_id)
        except (TypeError, ValueError):
            return redirect('attendance_home')

        students = Student.objects.filter(std_class_id=class_id, std_section_id=section_id)

        # Get class and section names
        selected_class = get_object_or_404(Class, id=class_id)
        selected_section = get_object_or_404(Section, id=section_id)

        # Get existing attendance for today
        from django.utils import timezone
        import pytz
        
        pakistan_tz = pytz.timezone('Asia/Karachi')
        pakistan_time = timezone.now().astimezone(pakistan_tz)
        today = pakistan_time.date()
        existing_attendance = Attendance.objects.filter(
            student__in=students,
            date=today
        ).select_related('student')
        
        # Add attendance data to students
        for student in students:
            student.attendance_status = None
            student.attendance_time = 'Not marked yet'
            
        for att in existing_attendance:
            for student in students:
                if student.id == att.student_id:
                    student.attendance_status = 'Present' if att.status == 'P' else 'Absent'
                    student.attendance_time = att.time_marked.strftime('%H:%M:%S') if att.time_marked else 'Not marked yet'
                    break

        return render(request, 'attendance.html', {
            'students': students,
            'class_id': class_id,
            'section_id': section_id,
            'selected_class_name': selected_class.class_name,
            'selected_section_name': selected_section.std_section,
            'classes': Class.objects.all(),
            'sections': Section.objects.all(),

        })
    return redirect('attendance_home')


from django.utils.timezone import now
from calendar import monthrange
from datetime import date

def save_attendance(request):
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        section_id = request.POST.get('section_id')
        
        if not class_id or not section_id:
            messages.error(request, "Class and section are required.")
            return redirect('attendance_home')

        student_ids = Student.objects.filter(std_class_id=class_id, std_section_id=section_id).values_list('id', flat=True)

        STATUS_MAP = {
            'Present': 'P',
            'Absent': 'A',
        }

        for student_id in student_ids:
            status_full = request.POST.get(f'status_{student_id}')
            print(f"Student ID: {student_id}, Status received: {status_full}")
            if status_full in STATUS_MAP:
                status = STATUS_MAP[status_full]
                print(f"Mapped status: {status}")
            else:
                continue  # Skip if no status selected

            from django.utils import timezone
            import pytz
            
            # Get Pakistan timezone
            pakistan_tz = pytz.timezone('Asia/Karachi')
            pakistan_time = timezone.now().astimezone(pakistan_tz)
            today = pakistan_time.date()
            current_time = pakistan_time
            
            print(f"Saving attendance for student {student_id} on date {today} with status {status}")
            
            # Delete any existing attendance for today and create new one
            Attendance.objects.filter(
                student_id=student_id,
                date=today
            ).delete()
            
            # Create new attendance record
            Attendance.objects.create(
                student_id=student_id,
                status=status,
                date=today,
                time_marked=current_time
            )

        messages.success(request, "Attendance saved successfully!")
        # Redirect back to attendance view with preserved values
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        url = reverse('attendance_view') + f'?class_id={class_id}&section_id={section_id}'
        return HttpResponseRedirect(url)

@admin_required
def student_monthly_report(request):
    classes = Class.objects.all()
    report_data = None
    selected_student = None
    
    # Get form values (from POST or GET for persistence)
    class_id = request.POST.get('class_id') or request.GET.get('class_id', '')
    section_id = request.POST.get('section_id') or request.GET.get('section_id', '')
    student_id = request.POST.get('student_id') or request.GET.get('student_id', '')
    
    # Handle month input field (format: YYYY-MM)
    report_month = request.POST.get('report_month') or request.GET.get('report_month', '')
    if report_month:
        year, month = report_month.split('-')
        year = int(year)
        month = int(month)
    else:
        month = date.today().month
        year = date.today().year
    
    if request.method == 'POST':
        
        if student_id:
            selected_student = get_object_or_404(Student, id=student_id)
            
            # Get attendance records with time_marked
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            start_date = datetime(year, month, 1).date()
            end_date = datetime(year, month, monthrange(year, month)[1]).date()
            
            print(f"Looking for attendance between {start_date} and {end_date}")
            
            attendance_records = Attendance.objects.filter(
                student_id=student_id,
                date__range=[start_date, end_date]
            ).values('date', 'status', 'time_marked')
            
            print(f"Found {len(attendance_records)} attendance records")
            for record in attendance_records:
                print(f"Record: Date={record['date']}, Status={record['status']}, Time={record['time_marked']}")
            
            attendance_dict = {record['date']: record for record in attendance_records}
            
            # Build report data with time_marked
            report_data = []
            current_date = start_date
            while current_date <= end_date:
                if current_date in attendance_dict:
                    record = attendance_dict[current_date]
                    # Debug print
                    print(f"Date: {current_date}, Status in DB: {record['status']}")
                    status = 'Present' if record['status'] == 'P' else 'Absent' if record['status'] == 'A' else 'Not Marked'
                    report_data.append({
                        'date': current_date,
                        'status': status,
                        'time_marked': record['time_marked']
                    })
                else:
                    report_data.append({
                        'date': current_date,
                        'status': 'Not Marked',
                        'time_marked': None
                    })
                current_date += timedelta(days=1)
            
            # Calculate statistics
            present_count = sum(1 for day in report_data if day['status'] == 'Present')
            absent_count = sum(1 for day in report_data if day['status'] == 'Absent')
            not_marked_count = sum(1 for day in report_data if day['status'] == 'Not Marked')
            
            return render(request, 'student_monthly_report.html', {
                'classes': classes,
                'report_data': report_data,
                'selected_student': selected_student,
                'selected_class_id': class_id,
                'selected_section_id': section_id,
                'selected_student_id': student_id,
                'year': year,
                'month': month,
                'selected_report_month': f"{year}-{month:02d}",
                'present_count': present_count,
                'absent_count': absent_count,
                'not_marked_count': not_marked_count,
                'total_days': len(report_data)
            })
    
    return render(request, 'student_monthly_report.html', {
        'classes': classes,
        'selected_class_id': class_id,
        'selected_section_id': section_id,
        'selected_student_id': student_id,
        'year': year,
        'month': month,
        'selected_report_month': f"{year}-{month:02d}"
    })

@admin_required
def create_user(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            # Save the user (password will be hashed automatically)
            form.save()
            messages.success(request, 'User created successfully!')
            return redirect('create_user')  # Redirect to the same page or to a list page
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CreateUserForm()
    
    return render(request, 'create_user.html', {'form': form})
@admin_required
def get_sections_for_class(request, class_id):
    sections = Section.objects.filter(class_name_id=class_id)
    section_list = [{'id': sec.id, 'std_section': sec.std_section} for sec in sections]
    return JsonResponse({'sections': section_list})

@admin_required
def get_students_for_section(request, class_id, section_id):
    students = Student.objects.filter(std_class_id=class_id, std_section_id=section_id, is_active=True)
    student_list = [{
        'id': student.id, 
        'std_fname': student.std_fname, 
        'std_lname': student.std_lname,
        'std_roll': student.std_roll
    } for student in students]
    return JsonResponse({'students': student_list})

@admin_required
def disable_batch(request):
    if request.method == 'POST':
        section_ids = request.POST.getlist('section_ids')

        # Deactivate all sections first
        Section.objects.update(is_active=False)

        # Activate the selected sections
        for section_id in section_ids:
            try:
                section = Section.objects.get(id=section_id)
                section.is_active = True
                section.save()
                messages.success(request, f"Section '{section.std_section}' activated successfully.")
            except Section.DoesNotExist:
                continue  # In case some invalid section ID is provided

        return redirect('disable_batch')  # Reload the page to reflect changes

    # Fetch all sections (or active sections) to display
    sections = Section.objects.all()

    return render(request, 'disable_batch.html', {'sections': sections})
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Username

def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')
        full_name = request.POST.get('full_name')
        profile_picture = request.FILES.get('profile_picture')
        
        try:
            user = Username(
                username=username,
                password=password,
                role=role,
                full_name=full_name,
                profile_picture=profile_picture
            )
            user.save()

            messages.success(request, 'User added successfully!')
            return redirect('add_user')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    # Get search query
    search = request.GET.get('search', '').strip()
    
    # Fetch users by role with search filter
    users = Username.objects.all()
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(full_name__icontains=search)
        )
    
    admins = users.filter(role="admin")
    teachers = users.filter(role="teacher")
    students = users.filter(role="student")

    return render(request, 'add_user.html', {
        "admins": admins,
        "teachers": teachers,
        "students": students,
        "search": search
    })

@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(Username, id=user_id)
    
    if request.method == 'POST':
        new_username = request.POST.get('username')
        
        # Check if username already exists (excluding current user)
        if Username.objects.filter(username=new_username).exclude(id=user.id).exists():
            messages.error(request, f"Username '{new_username}' is already taken. Please choose a different username.")
            return render(request, 'edit_user.html', {'user': user})
        
        try:
            user.username = new_username
            new_full_name = request.POST.get('full_name')
            user.role = request.POST.get('role')
            
            # Update names in respective profiles
            if user.role == 'teacher' and hasattr(user, 'teacher_profile'):
                names = new_full_name.split(' ', 1)
                user.teacher_profile.teacher_fname = names[0]
                user.teacher_profile.teacher_lname = names[1] if len(names) > 1 else ''
                user.teacher_profile.save()
            elif user.role == 'student' and hasattr(user, 'student_profile'):
                names = new_full_name.split(' ', 1)
                user.student_profile.std_fname = names[0]
                user.student_profile.std_lname = names[1] if len(names) > 1 else ''
                user.student_profile.save()
            else:
                user.full_name = new_full_name
            
            # Update password if provided
            new_password = request.POST.get('password')
            if new_password:
                user.password = new_password
                user._password_changed = True
            
            if request.FILES.get('profile_picture'):
                user.profile_picture = request.FILES.get('profile_picture')
            
            user.save()
            messages.success(request, "User updated successfully.")
            return redirect('add_user')
        except IntegrityError:
            messages.error(request, "Username already exists. Please choose a different username.")
            return render(request, 'edit_user.html', {'user': user})
    
    return render(request, 'edit_user.html', {'user': user})

@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(Username, id=user_id)
    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('add_user')

@admin_required
def studentss(request):
    print("user_id:", request.session.get('user_id'))
    print("user_role:", request.session.get('user_role'))

    classes = Class.objects.all()
    sections = Section.objects.all()
    context = {
        'classes': classes,
        'sections': sections,
        'form_data': {},
    }

    if request.method == "POST":
        std_fname = request.POST.get('first_name')
        std_lname = request.POST.get('last_name')
        dob = request.POST.get('dob')
        std_roll = request.POST.get('std_roll')
        class_id = request.POST.get('class')
        section_id = request.POST.get('section')
        gender = request.POST.get('gender')
        guardian_name1 = request.POST.get('guardian_name1')
        guardian_contact1 = request.POST.get('guardian_contact1')
        guardian_name2 = request.POST.get('guardian_name2')
        guardian_contact2 = request.POST.get('guardian_contact2')
        fee_discount = request.POST.get('discount_amount') if request.POST.get('discount_amount') else 0
        username_str = request.POST.get('username')
        password = request.POST.get('password')
        address = request.POST.get('address')
        profile_picture = request.FILES.get('profile_picture')

        context['form_data'] = request.POST  # Preserve form data on error

        # Validate required fields like address and gender
        if not address or address.strip() == '':
            messages.error(request, "Address is required.")
            return render(request, 'students.html', context)

        if not gender or gender == 'Not Selected':
            messages.error(request, "Please select a gender.")
            return render(request, 'students.html', context)

        try:
            std_class = Class.objects.get(id=class_id)
            std_section = Section.objects.get(id=section_id) if section_id else None

            # Check if roll number exists for this class
            existing_student = Student.objects.filter(std_class=std_class, std_roll=std_roll).first()
            if existing_student:
                messages.error(
                    request,
                    f"Roll number {std_roll} already assigned to {existing_student.std_fname} {existing_student.std_lname} in class {std_class.class_name}. Please choose a different roll number."
                )
                return render(request, 'students.html', context)

            # Check if username already exists
            if Username.objects.filter(username=username_str).exists():
                messages.error(request, f"Username '{username_str}' is already taken. Please choose a different username.")
                return render(request, 'students.html', context)

            hashed_password = make_password(password)
            new_username = Username.objects.create(username=username_str, password=hashed_password, role='student')

            new_student = Student(
                std_fname=std_fname,
                std_lname=std_lname,
                std_dob=dob,
                std_roll=std_roll,
                std_class=std_class,
                std_section=std_section,
                gender=gender,
                guardian_name=guardian_name1,
                guardian_contact1=guardian_contact1,
                guardian_contact2=guardian_contact2,
                discount_amount=fee_discount,
                username=new_username,
                address=address,
                profile_picture=profile_picture
            )
            new_student.save()
            
            # Log the activity
            log_user_activity(request, 'create', 'Student', new_student.id, 
                f'Created student: {new_student.std_fname} {new_student.std_lname} (Roll: {new_student.std_roll}, Class: {new_student.std_class.class_name})')

            messages.success(request, "Student created successfully.")
            return redirect('list_students')

        except Class.DoesNotExist:
            messages.error(request, "Selected class does not exist.")
        except Section.DoesNotExist:
            messages.error(request, "Selected section does not exist.")
        except IntegrityError as e:
            messages.error(request, f"Database error: {str(e)}")

    return render(request, 'students.html', context)

@admin_required
def list_students(request):
    # Get all classes and sections
    class_list = Class.objects.all()
    section_list = Section.objects.all()

    # Get filters from GET request
    search_name = request.GET.get('name', '').strip()
    search_class = request.GET.get('class', '').strip()
    search_section = request.GET.get('section', '').strip()

    # Initialize query
    students = Student.objects.all()

    # Apply name filter
    if search_name:
        students = students.filter(
            Q(std_fname__icontains=search_name) |
            Q(std_lname__icontains=search_name)
        )

    # Apply class filter
    if search_class:
        students = students.filter(std_class__class_name__icontains=search_class)

    # Apply section filter (convert to int safely)
    if search_section.isdigit():
        students = students.filter(std_section__id=int(search_section))  # Corrected to use section ID explicitly

    # Safe fallback for empty students
    if not students:
        students = []

    # Prepare the filter data to pass back to the template
    filters = {
        'name': search_name,
        'class': search_class,
        'section': search_section
    }

    # Return the filtered students and filter data to the template
    context = {
        'students': students,
        'class_list': class_list,
        'section_list': section_list,
        'filters': filters
    }

    return render(request, 'List_students.html', context)
@admin_required
def edit_students(request, student_id):
    student = get_object_or_404(StudentModel, id=student_id)
    classes = Class.objects.all()
    sections = Section.objects.all()

    if request.method == "POST":
        std_fname = request.POST.get('first_name')
        std_lname = request.POST.get('last_name')
        dob = request.POST.get('dob')
        std_roll = request.POST.get('std_roll')
        class_id = request.POST.get('class')
        section_id = request.POST.get('section')
        gender = request.POST.get('gender')
        guardian_name = request.POST.get('guardian_name')
        guardian_contact1 = request.POST.get('guardian_contact1')
        guardian_contact2 = request.POST.get('guardian_contact2')
        fee_discount = request.POST.get('discount_amount') or 0
        address = request.POST.get('address')

        try:
            student.std_fname = std_fname
            student.std_lname = std_lname
            student.std_dob = dob
            student.std_roll = std_roll
            student.std_class = Class.objects.get(id=class_id)  # <-- Correct field here
            student.std_section = Section.objects.get(id=section_id) if section_id else None
            student.gender = gender
            student.guardian_name = guardian_name
            student.guardian_contact1 = guardian_contact1
            student.guardian_contact2 = guardian_contact2
            student.discount_amount = fee_discount
            student.address = address

            student.save()
            
            # Log the activity
            try:
                user = Username.objects.get(id=request.session.get('user_id'))
                UserActivityLog.objects.create(
                    user=user,
                    action_type='update',
                    model_name='Student',
                    object_id=str(student.id),
                    description=f'Updated student: {student.std_fname} {student.std_lname} (Roll: {student.std_roll})'
                )
            except:
                pass
            
            return redirect('list_students')  # Redirect to your list page
        except Class.DoesNotExist:
            pass
        except Section.DoesNotExist:
            pass

    return render(request, 'edit_students.html', {
        'student': student,
        'classes': classes,
        'sections': sections,
    })
@admin_required
def edit_batch(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    sections = class_obj.sections.all()  # Get all sections for this class

    if request.method == 'POST':
        # Update class information if needed (e.g., renaming)
        class_name = request.POST.get('class_name')
        if class_name:
            class_obj.class_name = class_name
            class_obj.save()
            messages.success(request, f"Class '{class_obj.class_name}' updated successfully!")

        # Process the section name updates
        for sec in sections:
            new_name = request.POST.get(f"section_{sec.id}")  # Get new name from form
            if new_name:
                sec.std_section = new_name
                sec.save()

        messages.success(request, "Class and sections updated successfully.")
        return redirect('batch_management')  # Redirect to the class management page

    return render(request, 'edit_batch.html', {'class': class_obj, 'sections': sections})

@admin_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        user = student.username  # This is the Username object
        student.delete()
        user.delete()
        messages.success(request, "Student and their username deleted successfully.")
    
    return redirect('list_students')  # Or wherever you want


@admin_required
def batch_management(request):
    if request.method == 'POST':
        # Handle class creation
        if 'create_class' in request.POST:
            class_name = request.POST.get('class_name')
            if class_name:
                try:
                    new_class = Class.objects.create(class_name=class_name)
                    messages.success(request, f"Class '{new_class.class_name}' created successfully!")
                except Exception as e:
                    messages.error(request, f"Error creating class: {e}")
            else:
                messages.error(request, "Class name is required.")
        
        # Handle section creation
        elif 'create_section' in request.POST:
            class_id = request.POST.get('class_id')
            section_name = request.POST.get('section_name')
            
            if section_name and class_id:
                try:
                    class_obj = Class.objects.get(id=class_id)
                    new_section = Section.objects.create(std_section=section_name, class_name=class_obj)
                    messages.success(request, f"Section '{new_section.std_section}' created successfully!")
                except Class.DoesNotExist:
                    messages.error(request, "Class not found.")
            else:
                messages.error(request, "Section name or class not provided.")

        # Handle section update
        elif 'updated_section' in request.POST:
            section_id = request.POST.get('section_id')
            new_section_name = request.POST.get('updated_section')

            try:
                section = Section.objects.get(id=section_id)
                section.std_section = new_section_name  # Update the section name
                section.save()

                messages.success(request, f"Section '{section.std_section}' updated successfully!")
            except Section.DoesNotExist:
                messages.error(request, "Section not found.")

        # Handle section deletion
        elif 'delete_section' in request.POST:
            section_id = request.POST.get('delete_section_id')
            try:
                section = Section.objects.get(id=section_id)
                section.delete()
                messages.success(request, f"Section '{section.std_section}' deleted successfully!")
            except Section.DoesNotExist:
                messages.error(request, "Section not found.")

        return redirect('batch_management')  # Reload the page to reflect changes

    # Fetch all the classes and sections to display them in the template
    classes = Class.objects.all()
    teachers = Teacher.objects.all()
    subjects = SectionSubject.objects.select_related('class_name', 'section').prefetch_related('assignments__teacher')

    context = {
        'classes': classes,
        'teachers': teachers,
        'subjects': subjects,
    }

    return render(request, 'batch_management.html', context)

@admin_required
def update_section(request, sec_id):
    # Get the section to be updated
    section = get_object_or_404(Section, id=sec_id)

    if request.method == 'POST':
        new_section_name = request.POST.get('updated_section')  # Get the new section name from the form

        if new_section_name:
            section.std_section = new_section_name  # Update the section name
            section.save()
            messages.success(request, f"Section '{section.std_section}' updated successfully!")
        else:
            messages.error(request, "Section name cannot be empty.")

        return redirect('batch_management')  # Redirect back to the batch management page

    return redirect('batch_management')  # If the method is not POST, redirect

from django.views.decorators.http import require_POST
@admin_required
@require_POST
def disable_section(request, sec_id):
    section = get_object_or_404(Section, id=sec_id)
    if request.method == "POST":
        section.is_active = not section.is_active  # Toggle
        section.save()
        messages.success(request, f"Section {'enabled' if section.is_active else 'disabled'} successfully.")
    return redirect('batch_management')


@admin_required
def delete_section(request, sec_id):
    # Get the section to be deleted
    section = get_object_or_404(Section, id=sec_id)
    section_name = section.std_section

    if request.method == 'POST':
        section.delete()
        messages.success(request, f"Section '{section_name}' deleted successfully!")

    return redirect('batch_management')  # Redirect back to the batch management page


def support(request):
    return render(request, 'support.html')


def logout_view(request):
    request.session.flush()  # Clear session to log out
    return render(request, 'logout.html')  # Show logout page with animation

@admin_required
def promote_batch(request):
    if request.method == "POST":
        form = PromoteBatchForm(request.POST)
        if form.is_valid():
            source_class = form.cleaned_data['source_class']
            source_section = form.cleaned_data['source_section']
            target_class = form.cleaned_data['target_class']
            target_section = form.cleaned_data['target_section']

            # Promote students
            students = Student.objects.filter(std_class=source_class, std_section=source_section)
            count = students.update(std_class=target_class, std_section=target_section)

            messages.success(request, f"{count} students promoted successfully.")
            return redirect('promote_batch')
    else:
        form = PromoteBatchForm()

    classes = Class.objects.prefetch_related('sections').all()
    return render(request, 'promote_batch.html', {'form': form, 'classes': classes})

@admin_required
def delete_disable_students(request):
    class_list = Class.objects.all()
    section_list = Section.objects.all()

    filters = {
        'class': request.GET.get('class', ''),
        'section': request.GET.get('section', '')
    }

    # Filter students based on GET
    students = Student.objects.all()
    if filters['class']:
        students = students.filter(std_class__class_name__icontains=filters['class'])
    if filters['section'].isdigit():
        students = students.filter(std_section__id=int(filters['section']))

    if request.method == "POST":
        selected_ids = request.POST.getlist('selected_students')
        action = request.POST.get('action')

        if not selected_ids:
            messages.warning(request, "No students selected.")
            return redirect('delete_disable_students')

        students_to_modify = Student.objects.filter(id__in=selected_ids)

        if action == "disable":
            students_to_modify.update(is_active=False)
            messages.success(request, f"{students_to_modify.count()} student(s) disabled successfully.")
        elif action == "enable":
            students_to_modify.update(is_active=True)
            messages.success(request, f"{students_to_modify.count()} student(s) enabled successfully.")
        elif action == "delete":
            count = students_to_modify.count()
            students_to_modify.delete()
            messages.success(request, f"{count} student(s) deleted permanently.")
        else:
            messages.error(request, "Invalid action selected.")

        return redirect('delete_disable_students')  # Refresh page after action

    context = {
        'students': students,
        'class_list': class_list,
        'section_list': section_list,
        'filters': filters,
    }

    return render(request, 'delete_disable_students.html', context)

@admin_required
def promote_students(request):
    class_list = Class.objects.all()

    filters = {
        'source_class': request.GET.get('source_class', ''),
        'source_section': request.GET.get('source_section', ''),
        'target_class': request.GET.get('target_class', ''),
        'target_section': request.GET.get('target_section', ''),
    }

    students = Student.objects.all()
    if filters['source_class'].isdigit():
        students = students.filter(std_class__id=int(filters['source_class']))
    if filters['source_section'].isdigit():
        students = students.filter(std_section__id=int(filters['source_section']))

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_students')
        source_cls = request.POST.get('source_class')
        source_sec = request.POST.get('source_section')
        target_cls = request.POST.get('target_class')
        target_sec = request.POST.get('target_section')

        if not selected_ids:
            messages.warning(request, "No students selected for promotion.")
            return redirect('promote_students')

        if not (target_cls and target_sec and target_cls.isdigit() and target_sec.isdigit()):
            messages.error(request, "Select both target class and section.")
            return redirect('promote_students')

        new_class = Class.objects.get(id=int(target_cls))
        new_section = Section.objects.get(id=int(target_sec))

        students_to_promote = Student.objects.filter(id__in=selected_ids)
        students_to_promote.update(std_class=new_class, std_section=new_section)

        messages.success(request, f"Promoted {students_to_promote.count()} student(s).")
        return redirect('promote_students')

    source_sections = Section.objects.filter(class_name_id=filters['source_class']) if filters['source_class'].isdigit() else []
    target_sections = source_sections  # initial assumption; dynamic fetch possible

    context = {
        'class_list': class_list,
        'source_sections': source_sections,
        'target_sections': target_sections,
        'filters': filters,
        'students': students,
    }
    return render(request, 'promote_students.html', context)


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Teacher, Student, TeacherAttendance


@admin_required
def teacher_attendance(request):
    teachers = Teacher.objects.all()
    today = now().date()
    
    # Check if attendance already exists for today
    existing_count = TeacherAttendance.objects.filter(date=today).count()
    is_update = existing_count > 0
    
    if request.method == 'POST':
        for teacher in teachers:
            status = request.POST.get(f'status_{teacher.id}')
            if status:
                attendance, created = TeacherAttendance.objects.get_or_create(
                    teacher=teacher,
                    date=today,
                    defaults={'status': status}
                )
                if not created:
                    attendance.status = status
                    attendance.save()
        
        action = "updated" if is_update else "saved"
        messages.success(request, f"Teacher attendance {action} successfully!")
        return redirect('teacher_attendance')
    
    # Get existing attendance for today
    existing_attendance = TeacherAttendance.objects.filter(date=today)
    attendance_dict = {att.teacher_id: att.status for att in existing_attendance}
    
    return render(request, 'teacher_attendance.html', {
        'teachers': teachers,
        'attendance_dict': attendance_dict,
        'is_update': is_update
    })

@admin_required
def teacher_attendance_report(request):
    teachers = Teacher.objects.all()
    report_data = None
    
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        
        if teacher_id and from_date and to_date:
            from datetime import datetime, timedelta
            start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            
            # Get all dates in range
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date)
                current_date += timedelta(days=1)
            
            # Get attendance records
            attendance_records = TeacherAttendance.objects.filter(
                teacher_id=teacher_id,
                date__range=[start_date, end_date]
            ).values('date', 'status', 'time_marked')
            
            attendance_dict = {record['date']: record for record in attendance_records}
            
            # Build report data
            report_data = []
            for date in date_range:
                if date in attendance_dict:
                    record = attendance_dict[date]
                    report_data.append({
                        'date': date,
                        'status': record['status'],
                        'time_marked': record['time_marked']
                    })
                else:
                    report_data.append({
                        'date': date,
                        'status': 'Not Marked',
                        'time_marked': None
                    })
            
            selected_teacher = Teacher.objects.get(id=teacher_id)
            return render(request, 'teacher_attendance_report.html', {
                'teachers': teachers,
                'report_data': report_data,
                'selected_teacher': selected_teacher,
                'from_date': from_date,
                'to_date': to_date
            })
    
    return render(request, 'teacher_attendance_report.html', {'teachers': teachers})

# Show all teachers



# Show teacher detail + their exams/marksheets
def teacher_detail(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    return render(request, "teachers/teacher_detail.html", {
        "teacher": teacher,
    })


# Add marks for a student
def add_marks(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if request.method == "POST":
        form = StudentTestResultForm(request.POST)
        if form.is_valid():
            result = form.save(commit=False)
            result.test = test
            result.save()
            messages.success(request, "Marks added successfully ✅")
            return redirect("session_detail", session_id=test.session.id)
    else:
        form = StudentTestResultForm()

    return render(request, "teachers/add_marks.html", {"form": form, "test": test})

@admin_required
def add_teacher(request):
    if request.method == 'POST':
        username_str = request.POST.get('username')
        password = request.POST.get('password')
        teacher_fname = request.POST.get('teacher_fname')
        teacher_lname = request.POST.get('teacher_lname')
        phone1 = request.POST.get('phone1')
        phone2 = request.POST.get('phone2')
        profile_picture = request.FILES.get('profile_picture')
        
        try:
            # Create username
            new_username = Username.objects.create(
                username=username_str,
                password=password,
                role='teacher'
            )
            
            # Create teacher
            Teacher.objects.create(
                username=new_username,
                teacher_fname=teacher_fname,
                teacher_lname=teacher_lname,
                phone1=phone1,
                phone2=phone2,
                profile_picture=profile_picture
            )
            
            # Log the activity
            log_user_activity(request, 'create', 'Teacher', teacher.id, 
                f'Created teacher: {teacher_fname} {teacher_lname}')
            
            messages.success(request, "Teacher created successfully.")
            return redirect('add_teacher')
            
        except Exception as e:
            messages.error(request, f"Error: {e}")
    
    teachers = Teacher.objects.all()
    print(f"Teachers count: {teachers.count()}")
    context = {'teachers': teachers}
    return render(request, 'add_teacher.html', context)

@admin_required
def fee_dashboard(request):
    # Dashboard showing overview
    total_fees = Fee.objects.count()
    total_students_with_fees = StudentFee.objects.values('student').distinct().count()
    total_paid = StudentFee.objects.filter(is_paid=True).count()
    total_unpaid = StudentFee.objects.filter(is_paid=False).count()
    
    return render(request, 'fee_dashboard.html', {
        'total_fees': total_fees,
        'total_students_with_fees': total_students_with_fees,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid
    })

@admin_required
def fee_management(request):
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        section_id = request.POST.get('section_id')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        
        try:
            fee = Fee.objects.create(
                class_name_id=class_id,
                section_id=section_id,
                amount=amount,
                description=description
            )
            
            # Log the action
            user = Username.objects.get(id=request.session.get('user_id'))
            FeeUpdateLog.objects.create(
                user=user,
                action_type='created',
                fee=fee,
                description=f"Created fee for {fee.class_name.class_name}-{fee.section.std_section}: PKR {amount} ({description})"
            )
            
            messages.success(request, "Fee added successfully.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        
        return redirect('fee_management')
    
    classes = Class.objects.all()
    sections = Section.objects.all()
    fees = Fee.objects.all().select_related('class_name', 'section')
    
    return render(request, 'fee_management.html', {
        'classes': classes,
        'sections': sections,
        'fees': fees
    })

@admin_required
def submit_fee(request, fee_id):
    fee = get_object_or_404(Fee, id=fee_id)
    
    if request.method == 'POST':
        month = request.POST.get('month')
        due_date = request.POST.get('due_date')
        
        if not month or not due_date:
            messages.error(request, "Month and due date are required.")
            return render(request, 'submit_fee.html', {'fee': fee})
        
        # Get all students in this class-section
        students = Student.objects.filter(
            std_class=fee.class_name,
            std_section=fee.section,
            is_active=True
        )
        
        if not students.exists():
            messages.error(request, f"No active students found in {fee.class_name.class_name}-{fee.section.std_section}.")
            return render(request, 'submit_fee.html', {'fee': fee})
        
        created_count = 0
        existing_count = 0
        
        try:
            for student in students:
                # Calculate discounted amount
                discounted_amount = fee.amount - student.discount_amount
                # Ensure amount is not negative
                final_amount = max(discounted_amount, 0)
                
                student_fee, created = StudentFee.objects.get_or_create(
                    student=student,
                    fee=fee,
                    month=month,
                    defaults={
                        'amount_due': final_amount,
                        'due_date': due_date
                    }
                )
                if created:
                    created_count += 1
                else:
                    existing_count += 1
            
            # Log the action
            user = Username.objects.get(id=request.session.get('user_id'))
            FeeUpdateLog.objects.create(
                user=user,
                action_type='submitted',
                fee=fee,
                description=f"Submitted fee to {created_count} students for {fee.class_name.class_name}-{fee.section.std_section} ({month})"
            )
            
            if created_count > 0:
                messages.success(request, f"Fee submitted for {created_count} students.")
            if existing_count > 0:
                messages.info(request, f"{existing_count} students already had this fee for {month}.")
                
        except Exception as e:
            messages.error(request, f"Error creating student fees: {str(e)}")
            return render(request, 'submit_fee.html', {'fee': fee})
        
        return redirect('fee_management')
    
    return render(request, 'submit_fee.html', {'fee': fee})

@admin_required
def fee_reports(request):
    # Get filter parameters
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    month = request.GET.get('month')
    status = request.GET.get('status')
    
    # Base query
    student_fees = StudentFee.objects.select_related('student', 'fee').all()
    
    # Apply filters
    if class_id:
        student_fees = student_fees.filter(fee__class_name_id=class_id)
    if section_id:
        student_fees = student_fees.filter(fee__section_id=section_id)
    if month:
        student_fees = student_fees.filter(month=month)
    if status == 'paid':
        student_fees = student_fees.filter(is_paid=True)
    elif status == 'unpaid':
        student_fees = student_fees.filter(is_paid=False)
    
    classes = Class.objects.all()
    sections = Section.objects.all()
    
    return render(request, 'fee_reports.html', {
        'student_fees': student_fees,
        'classes': classes,
        'sections': sections,
        'filters': {
            'class_id': class_id,
            'section_id': section_id,
            'month': month,
            'status': status
        }
    })

@admin_required
def defaulter_list(request):
    classes = Class.objects.all()
    sections = Section.objects.all()
    
    filters = {
        'class_id': request.GET.get('class_id', ''),
        'section_id': request.GET.get('section_id', ''),
        'month': request.GET.get('month', '')
    }
    
    # Get unpaid fees (not just overdue)
    defaulters = StudentFee.objects.filter(
        is_paid=False
    ).select_related('student', 'fee')
    
    # Apply filters
    if filters['class_id']:
        defaulters = defaulters.filter(fee__class_name_id=filters['class_id'])
    if filters['section_id']:
        defaulters = defaulters.filter(fee__section_id=filters['section_id'])
    if filters['month']:
        defaulters = defaulters.filter(month=filters['month'])
    
    defaulters = defaulters.order_by('fee__class_name__class_name', 'fee__section__std_section', 'student__std_roll')
    
    return render(request, 'defaulter_list.html', {
        'defaulters': defaulters,
        'classes': classes,
        'sections': sections,
        'filters': filters
    })

@admin_required
def bulk_fee_collection(request):
    classes = Class.objects.all()
    sections = Section.objects.all()
    student_fees = []
    
    filters = {
        'class_id': request.GET.get('class_id', ''),
        'section_id': request.GET.get('section_id', ''),
        'month': request.GET.get('month', ''),
        'search': request.GET.get('search', '')
    }
    
    if request.method == 'POST':
        selected_fee_ids = request.POST.getlist('selected_fees')
        payment_method = request.POST.get('payment_method')
        
        if selected_fee_ids:
            updated_count = 0
            for fee_id in selected_fee_ids:
                try:
                    student_fee = StudentFee.objects.get(id=fee_id, is_paid=False)
                    student_fee.amount_paid = student_fee.amount_due
                    student_fee.is_paid = True
                    student_fee.payment_date = now().date()
                    student_fee.save()
                    
                    FeePayment.objects.create(
                        student_fee=student_fee,
                        amount_paid=student_fee.amount_due,
                        payment_method=payment_method
                    )
                    updated_count += 1
                except StudentFee.DoesNotExist:
                    continue
            
            messages.success(request, f"{updated_count} fee(s) marked as paid successfully!")
        else:
            messages.warning(request, "No fees selected.")
        
        return redirect('bulk_fee_collection')
    
    if filters['month']:
        student_fees = StudentFee.objects.filter(
            month=filters['month']
        ).select_related('student', 'fee')
        
        if filters['class_id']:
            student_fees = student_fees.filter(fee__class_name_id=filters['class_id'])
        if filters['section_id']:
            student_fees = student_fees.filter(fee__section_id=filters['section_id'])
        if filters['search']:
            student_fees = student_fees.filter(
                Q(student__std_fname__icontains=filters['search']) |
                Q(student__std_lname__icontains=filters['search']) |
                Q(student__std_roll__icontains=filters['search'])
            )
        
        student_fees = student_fees.order_by('student__std_roll')
    
    return render(request, 'bulk_fee_collection.html', {
        'classes': classes,
        'sections': sections,
        'student_fees': student_fees,
        'filters': filters
    })

@admin_required
def mark_fee_paid(request, student_fee_id):
    student_fee = get_object_or_404(StudentFee, id=student_fee_id)
    
    if request.method == 'POST':
        amount_paid = request.POST.get('amount_paid')
        payment_method = request.POST.get('payment_method')
        
        student_fee.amount_paid = amount_paid
        student_fee.is_paid = True
        student_fee.payment_date = now().date()
        student_fee.save()
        
        # Create payment record
        payment = FeePayment.objects.create(
            student_fee=student_fee,
            amount_paid=amount_paid,
            payment_method=payment_method
        )
        
        # Log the action
        user = Username.objects.get(id=request.session.get('user_id'))
        FeeUpdateLog.objects.create(
            user=user,
            action_type='payment',
            student_fee=student_fee,
            description=f"Recorded payment of PKR {amount_paid} for {student_fee.student.std_fname} {student_fee.student.std_lname} ({student_fee.month}) via {payment_method}"
        )
        
        # Log the activity
        log_user_activity(request, 'update', 'StudentFee', student_fee.id, 
            f'Recorded fee payment: PKR {amount_paid} for {student_fee.student.std_fname} {student_fee.student.std_lname} ({student_fee.month})')
        
        messages.success(request, "Fee payment recorded successfully.")
        return redirect('fee_reports')
    
    return render(request, 'mark_fee_paid.html', {'student_fee': student_fee})

@admin_required
def edit_fee(request, fee_id):
    fee = get_object_or_404(Fee, id=fee_id)
    
    if request.method == 'POST':
        fee.description = request.POST.get('description')
        fee.amount = request.POST.get('amount')
        fee.save()
        messages.success(request, "Fee updated successfully!")
        return redirect('fee_management')
    
    classes = Class.objects.all()
    sections = Section.objects.all()
    
    return render(request, 'edit_fee.html', {
        'fee': fee,
        'classes': classes,
        'sections': sections
    })

@admin_required
def delete_fee(request, fee_id):
    fee = get_object_or_404(Fee, id=fee_id)
    
    if request.method == 'POST':
        # Delete all student fees associated with this fee
        StudentFee.objects.filter(fee=fee).delete()
        # Delete the fee itself
        fee.delete()
        messages.success(request, f"Fee for {fee.class_name.class_name}-{fee.section.std_section} deleted successfully!")
        return redirect('fee_management')
    
    return redirect('fee_management')

@admin_required
def barcode_fee_entry(request):
    if request.method == 'GET':
        return render(request, 'barcode_fee_entry.html')
    
    elif request.method == 'POST':
        import json
        data = json.loads(request.body)
        barcode = data.get('barcode')
        month = data.get('month')
        payment_method = data.get('payment_method', 'Cash')
        
        try:
            # Find student by roll number (using barcode as roll number)
            student = Student.objects.get(std_roll=barcode)
            
            # Get all pending fees for this student
            pending_fees = StudentFee.objects.filter(
                student=student,
                is_paid=False
            ).select_related('fee')
            
            # Find specific fee for this month
            student_fee = StudentFee.objects.filter(
                student=student,
                month=month,
                is_paid=False
            ).first()
            
            if not student_fee:
                return JsonResponse({
                    'success': False,
                    'error': f'No unpaid fee found for {student.std_fname} {student.std_lname} for {month}',
                    'student': {
                        'name': f'{student.std_fname} {student.std_lname}',
                        'class': student.std_class.class_name,
                        'section': student.std_section.std_section if student.std_section else 'N/A',
                        'roll': student.std_roll,
                        'guardian': student.guardian_name,
                        'pending_fees': [{
                            'description': fee.fee.description,
                            'month': fee.month,
                            'amount': fee.amount_due
                        } for fee in pending_fees]
                    }
                })
            
            # Mark fee as paid
            student_fee.amount_paid = student_fee.amount_due
            student_fee.is_paid = True
            student_fee.payment_date = now().date()
            student_fee.save()
            
            # Create payment record
            payment = FeePayment.objects.create(
                student_fee=student_fee,
                amount_paid=student_fee.amount_due,
                payment_method=payment_method
            )
            
            # Get updated pending fees
            remaining_pending = StudentFee.objects.filter(
                student=student,
                is_paid=False
            ).select_related('fee')
            
            return JsonResponse({
                'success': True,
                'student': {
                    'name': f'{student.std_fname} {student.std_lname}',
                    'class': student.std_class.class_name,
                    'section': student.std_section.std_section if student.std_section else 'N/A',
                    'roll': student.std_roll,
                    'guardian': student.guardian_name,
                    'pending_fees': [{
                        'description': fee.fee.description,
                        'month': fee.month,
                        'amount': fee.amount_due
                    } for fee in remaining_pending]
                },
                'amount': str(student_fee.amount_due),
                'voucher_url': f'/print_voucher/{payment.id}/'
            })
            
        except Student.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Student with roll number {barcode} not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error processing payment: {str(e)}'
            })

@admin_required
def voucher_generator(request):
    classes = Class.objects.all()
    sections = Section.objects.all()
    students_with_arrears = []
    
    filters = {
        'class_id': request.GET.get('class_id', ''),
        'section_id': request.GET.get('section_id', '')
    }
    
    if filters['class_id'] and filters['section_id']:
        students = Student.objects.filter(
            std_class_id=filters['class_id'],
            std_section_id=filters['section_id']
        )
        
        for student in students:
            unpaid_fees = StudentFee.objects.filter(
                student=student,
                is_paid=False
            )
            
            if unpaid_fees.exists():
                total_arrears = sum(fee.amount_due for fee in unpaid_fees)
                students_with_arrears.append({
                    'student': student,
                    'pending_count': unpaid_fees.count(),
                    'total_arrears': total_arrears
                })
    
    return render(request, 'voucher_generator.html', {
        'classes': classes,
        'sections': sections,
        'students_with_arrears': students_with_arrears,
        'filters': filters
    })

@admin_required
def print_single_voucher(request, student_id):
    from django.utils import timezone
    import barcode
    from barcode.writer import ImageWriter
    from io import BytesIO
    import base64
    
    student = get_object_or_404(Student, id=student_id)
    arrears = StudentFee.objects.filter(student=student, is_paid=False)
    total_arrears = sum(fee.amount_due for fee in arrears)
    
    # Generate barcode
    barcode_value = f"{student.std_roll:04d}"
    code128 = barcode.get_barcode_class('code128')
    barcode_instance = code128(barcode_value, writer=ImageWriter())
    buffer = BytesIO()
    barcode_instance.write(buffer)
    barcode_data = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'print_voucher.html', {
        'student': student,
        'arrears': arrears,
        'total_arrears': total_arrears,
        'barcode_data': barcode_data,
        'printed_date': timezone.now().strftime('%Y-%m-%d')
    })

@admin_required
def print_vouchers(request):
    from django.utils import timezone
    import barcode
    from barcode.writer import ImageWriter
    from io import BytesIO
    import base64
    
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    
    students = Student.objects.filter(
        std_class_id=class_id,
        std_section_id=section_id
    )
    
    vouchers_data = []
    for student in students:
        arrears = StudentFee.objects.filter(student=student, is_paid=False)
        if arrears.exists():
            total_arrears = sum(fee.amount_due for fee in arrears)
            
            # Generate barcode for each student
            barcode_value = f"{student.std_roll:04d}"
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(barcode_value, writer=ImageWriter())
            buffer = BytesIO()
            barcode_instance.write(buffer)
            barcode_data = base64.b64encode(buffer.getvalue()).decode()
            
            vouchers_data.append({
                'student': student,
                'arrears': arrears,
                'total_arrears': total_arrears,
                'barcode_data': barcode_data
            })
    
    return render(request, 'print_multiple_vouchers.html', {
        'vouchers_data': vouchers_data,
        'printed_date': timezone.now().strftime('%Y-%m-%d')
    })

@admin_required
def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST':
        teacher.teacher_fname = request.POST.get('teacher_fname')
        teacher.teacher_lname = request.POST.get('teacher_lname')
        teacher.phone1 = request.POST.get('phone1')
        teacher.phone2 = request.POST.get('phone2')
        teacher.save()
        messages.success(request, "Teacher updated successfully.")
        return redirect('add_teacher')
    return render(request, 'edit_teacher.html', {'teacher': teacher})

@admin_required
def delete_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    username = teacher.username
    teacher.delete()
    username.delete()
    messages.success(request, "Teacher deleted successfully.")
    return redirect('add_teacher')

# Update marks
def update_marks(request, result_id):
    result = get_object_or_404(StudentTestResult, id=result_id)

    if request.method == "POST":
        form = StudentTestResultForm(request.POST, instance=result)
        if form.is_valid():
            form.save()
            messages.success(request, "Marks updated successfully ✏️")
            return redirect("session_detail", session_id=result.test.session.id)
    else:
        form = StudentTestResultForm(instance=result)

    return render(request, "teachers/update_marks.html", {"form": form, "result": result})


# Delete marks
def delete_marks(request, result_id):
    result = get_object_or_404(StudentTestResult, id=result_id)
    session_id = result.test.session.id

    if request.method == "POST":
        result.delete()
        messages.success(request, "Marks deleted ❌")
        return redirect("session_detail", session_id=session_id)

    return render(request, "teachers/delete_marks.html", {"result": result})

# Attendance Notification Functions
def attendance_notification_log(request):
    """Show students with unsent attendance notifications"""
    from django.utils import timezone
    today = timezone.now().date()
    
    # Get today's attendance records
    todays_attendance = Attendance.objects.filter(date=today).select_related('student')
    
    # Get or create notification records
    pending_notifications = []
    for attendance in todays_attendance:
        notification, created = AttendanceNotification.objects.get_or_create(
            student=attendance.student,
            attendance=attendance,
            defaults={'notification_sent': False}
        )
        
        if not notification.notification_sent:
            pending_notifications.append({
                'id': notification.id,
                'student_name': f"{attendance.student.std_fname} {attendance.student.std_lname}",
                'class': attendance.student.std_class.class_name,
                'section': attendance.student.std_section.std_section if attendance.student.std_section else 'N/A',
                'status': 'Present' if attendance.status == 'P' else 'Absent',
                'phone': attendance.student.guardian_contact1 or attendance.student.guardian_contact2,
                'date': attendance.date
            })
    
    return render(request, 'attendance_notifications.html', {
        'pending_notifications': pending_notifications,
        'total_pending': len(pending_notifications)
    })

def send_notification(request):
    """Send WhatsApp notification for specific student"""
    if request.method == 'POST':
        try:
            import json
            from django.utils import timezone
            import threading
            
            data = json.loads(request.body)
            notification_id = data.get('notification_id')
            
            notification = AttendanceNotification.objects.get(id=notification_id)
            student = notification.student
            attendance = notification.attendance
            
            # Get phone number
            phone = student.guardian_contact1 or student.guardian_contact2
            if not phone:
                return JsonResponse({'success': False, 'error': 'No phone number found'})
            
            # Format phone number
            if hasattr(phone, 'as_e164'):
                phone_str = phone.as_e164
            else:
                phone_str = str(phone)
            
            # Create message
            status_text = 'Present' if attendance.status == 'P' else 'Absent'
            message = f"Dear Parent,\n\nYour child {student.std_fname} {student.std_lname} from {student.std_class.class_name}-{student.std_section.std_section if student.std_section else 'N/A'} was {status_text} today ({attendance.date}).\n\nThank you,\nSchool Administration"
            
            # Mark as sent immediately
            notification.notification_sent = True
            notification.sent_at = timezone.now()
            notification.save()
            
            return JsonResponse({'success': True, 'message': 'Notification sent!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def send_all_notifications(request):
    """Send notifications to all pending students"""
    if request.method == 'POST':
        try:
            from django.utils import timezone
            
            pending = AttendanceNotification.objects.filter(notification_sent=False)
            count = pending.count()
            
            # Mark all as sent
            pending.update(notification_sent=True, sent_at=timezone.now())
            
            return JsonResponse({'success': True, 'message': f'Marked {count} notifications as sent!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def get_pending_count(request):
    """Get count of pending notifications"""
    count = AttendanceNotification.objects.filter(notification_sent=False).count()
    return JsonResponse({'pending_count': count})

@admin_required
def get_message_templates(request):
    """Get message templates by type"""
    template_type = request.GET.get('type', 'general')
    templates = MessageTemplate.objects.filter(
        template_type=template_type,
        is_active=True
    ).values('id', 'name', 'message_text')
    
    return JsonResponse({'templates': list(templates)})

@admin_required
def create_message_template(request):
    """Create new message template"""
    if request.method == 'POST':
        name = request.POST.get('name')
        template_type = request.POST.get('template_type')
        message_text = request.POST.get('message_text')
        
        MessageTemplate.objects.create(
            name=name,
            template_type=template_type,
            message_text=message_text
        )
        
        messages.success(request, 'Template created successfully!')
        return redirect('message_templates')
    
    template_type = request.GET.get('type', 'general')
    return render(request, 'create_message_template.html', {
        'template_type': template_type,
        'template_types': MessageTemplate.TEMPLATE_TYPES
    })

@admin_required
def edit_message_template(request, template_id):
    """Edit message template"""
    template = get_object_or_404(MessageTemplate, id=template_id)
    
    if request.method == 'POST':
        template.name = request.POST.get('name')
        template.template_type = request.POST.get('template_type')
        template.message_text = request.POST.get('message_text')
        template.save()
        
        messages.success(request, 'Template updated successfully!')
        return redirect('message_templates')
    
    return render(request, 'edit_message_template.html', {
        'template': template,
        'template_types': MessageTemplate.TEMPLATE_TYPES
    })

@admin_required
def message_templates(request):
    """List all message templates"""
    templates = MessageTemplate.objects.all().order_by('template_type', 'name')
    return render(request, 'message_templates.html', {
        'templates': templates,
        'template_types': MessageTemplate.TEMPLATE_TYPES
    })

@admin_required
def fee_logs(request):
    """Display fee update logs"""
    logs = FeeUpdateLog.objects.all().select_related('user', 'fee', 'student_fee').order_by('-timestamp')
    
    # Filter by date range if provided
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    action_type = request.GET.get('action_type')
    
    if from_date:
        logs = logs.filter(timestamp__date__gte=from_date)
    if to_date:
        logs = logs.filter(timestamp__date__lte=to_date)
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    return render(request, 'fee_logs.html', {
        'logs': logs,
        'action_types': FeeUpdateLog.ACTION_TYPES,
        'filters': {
            'from_date': from_date,
            'to_date': to_date,
            'action_type': action_type
        }
    })

@admin_required
def test_management(request):
    """Test management dashboard"""
    sessions = TestSession.objects.all().select_related('class_name', 'section')
    classes = Class.objects.all()
    
    return render(request, 'test_management.html', {
        'sessions': sessions,
        'classes': classes
    })

@admin_required
def create_test_session(request):
    """Create new test session"""
    if request.method == 'POST':
        name = request.POST.get('name')
        session_type = request.POST.get('session_type')
        class_sections = request.POST.getlist('class_sections')
        month = request.POST.get('month')
        year = month.split('-')[0] if month else None
        
        if not class_sections:
            messages.error(request, 'Please select at least one class and section.')
            return render(request, 'create_test_session.html', {'classes': Class.objects.prefetch_related('sections')})
        
        try:
            created_count = 0
            for class_section in class_sections:
                class_id, section_id = class_section.split('_')
                TestSession.objects.create(
                    name=name,
                    session_type=session_type,
                    class_name_id=class_id,
                    section_id=section_id,
                    month=month,
                    year=year
                )
                created_count += 1
            
            messages.success(request, f'Test session created for {created_count} class-sections successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        
        return redirect('test_management')
    
    classes = Class.objects.prefetch_related('sections').all()
    return render(request, 'create_test_session.html', {'classes': classes})

@admin_required
def session_detail(request, session_id):
    """View and manage tests in a session"""
    session = get_object_or_404(TestSession, id=session_id)
    tests = session.tests.all()
    
    # Get subjects for this class/section
    subjects = SectionSubject.objects.filter(
        class_name=session.class_name,
        section=session.section,
        is_active=True
    ).values_list('subject', flat=True)
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        total_marks = request.POST.get('total_marks')
        test_date = request.POST.get('test_date')
        
        try:
            Test.objects.create(
                session=session,
                subject=subject,
                test_name=request.POST.get('test_name'),
                total_marks=total_marks,
                test_date=test_date
            )
            messages.success(request, 'Test added successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        
        return redirect('session_detail', session_id=session_id)
    
    return render(request, 'session_detail.html', {
        'session': session,
        'tests': tests,
        'subjects': subjects
    })

@admin_required
def enter_marks(request, test_id):
    """Enter marks for students in a test"""
    test = get_object_or_404(Test, id=test_id)
    students = Student.objects.filter(
        std_class=test.session.class_name,
        std_section=test.session.section,
        is_active=True
    ).order_by('std_roll')
    
    print(f"Debug: Found {students.count()} students for class {test.session.class_name} section {test.session.section}")
    
    if request.method == 'POST':
        for student in students:
            marks = request.POST.get(f'marks_{student.id}')
            remarks = request.POST.get(f'remarks_{student.id}', '')
            
            if marks:
                StudentTestResult.objects.update_or_create(
                    student=student,
                    test=test,
                    defaults={
                        'obtained_marks': float(marks),
                        'remarks': remarks
                    }
                )
        
        # Log the activity
        try:
            user = Username.objects.get(id=request.session.get('user_id'))
            UserActivityLog.objects.create(
                user=user,
                action_type='update',
                model_name='StudentTestResult',
                object_id=str(test.id),
                description=f'Updated marks for {test.subject} - {test.test_name} in {test.session.class_name.class_name}-{test.session.section.std_section}'
            )
        except:
            pass
        
        # Log the activity
        log_user_activity(request, 'update', 'StudentTestResult', test.id, 
            f'Entered marks for test: {test.test_name} ({test.subject}) - {test.session.class_name.class_name}-{test.session.section.std_section}')
        
        messages.success(request, 'Marks entered successfully!')
        return redirect('session_detail', session_id=test.session.id)
    
    # Get existing results
    existing_results = StudentTestResult.objects.filter(test=test)
    results_dict = {result.student_id: result for result in existing_results}
    
    # Add existing marks to students
    for student in students:
        if student.id in results_dict:
            student.existing_marks = results_dict[student.id].obtained_marks
            student.existing_remarks = results_dict[student.id].remarks
        else:
            student.existing_marks = ''
            student.existing_remarks = ''
    
    return render(request, 'enter_marks.html', {
        'test': test,
        'students': students
    })

@admin_required
def print_result_cards(request, session_id):
    """Print result cards for all students in a session"""
    session = get_object_or_404(TestSession, id=session_id)
    
    if session.session_type == 'monthly test':
        return print_monthly_test_cards(request, session)
    else:
        return print_session_exam_cards(request, session)

def print_monthly_test_cards(request, session):
    """Print monthly test result cards"""
    students = Student.objects.filter(
        std_class=session.class_name,
        std_section=session.section,
        is_active=True
    ).order_by('std_roll')
    
    student_results = []
    for student in students:
        results = MonthlyTestResult.objects.filter(
            student=student,
            test__class_name=session.class_name,
            test__section=session.section,
            test__month=session.month,
            test__year=session.year
        ).select_related('test')
        
        results_data = []
        for result in results:
            results_data.append({
                'subject': result.test.subject,
                'total_marks': result.test.total_marks,
                'obtained_marks': result.obtained_marks
            })
        
        total_marks = sum(item['total_marks'] for item in results_data)
        obtained_marks = sum(item['obtained_marks'] for item in results_data)
        percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
        
        student_results.append({
            'student': student,
            'results': results_data,
            'total_marks': total_marks,
            'obtained_marks': obtained_marks,
            'percentage': percentage,
            'grade': get_grade(percentage)
        })
    
    return render(request, 'print_result_cards.html', {
        'session': session,
        'student_results': student_results
    })

def print_session_exam_cards(request, session):
    """Print session exam result cards"""
    students = Student.objects.filter(
        std_class=session.class_name,
        std_section=session.section,
        is_active=True
    ).order_by('std_roll')
    
    student_results = []
    for student in students:
        subjects = {}
        for result in StudentTestResult.objects.filter(student=student, test__session=session):
            subj = result.test.subject
            test_name = result.test.test_name
            if subj not in subjects:
                subjects[subj] = {
                    "T1": {"tm": "-", "om": "-"},
                    "T2": {"tm": "-", "om": "-"},
                    "T3": {"tm": "-", "om": "-"},
                    "T4": {"tm": "-", "om": "-"},
                    "total_tm": 0,
                    "total_om": 0,
                }
            if test_name in subjects[subj]:
                subjects[subj][test_name]["tm"] = result.test.total_marks
                subjects[subj][test_name]["om"] = result.obtained_marks or 0
                subjects[subj]["total_tm"] += result.test.total_marks
                subjects[subj]["total_om"] += result.obtained_marks or 0
        
        # Calculate percentage per subject
        for subj, data in subjects.items():
            if data["total_tm"] > 0:
                data["percentage"] = (data["total_om"] / data["total_tm"]) * 100
            else:
                data["percentage"] = 0
        
        # Calculate overall percentage
        total_marks = sum([s.get('total_tm', 0) for s in subjects.values()])
        obtained_marks = sum([s.get('total_om', 0) for s in subjects.values()])
        percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
        
        student_results.append({
            'student': student,
            'subjects': subjects,
            'total_marks': total_marks,
            'obtained_marks': obtained_marks,
            'percentage': percentage,
            'grade': get_grade(percentage)
        })
    
    # Calculate positions
    if student_results:
        sorted_results = sorted(student_results, key=lambda x: x['percentage'], reverse=True)
        for i, result in enumerate(sorted_results):
            result['position'] = i + 1
    
    # Log the activity
    log_user_activity(request, 'view', 'TestSession', session.id, 
        f'Printed result cards for session: {session.name} - {session.class_name.class_name}-{session.section.std_section}')
    
    return render(request, 'print_session_exam_cards.html', {
        'session': session,
        'student_results': student_results
    })

def get_grade(percentage):
    """Calculate grade based on percentage"""
    if percentage >= 90: return 'A+'
    elif percentage >= 80: return 'A'
    elif percentage >= 70: return 'B'
    elif percentage >= 60: return 'C'
    elif percentage >= 50: return 'D'
    else: return 'F'

@admin_required
def get_subjects_for_session(request, class_id, section_id):
    """Get subjects for a specific class and section"""
    subjects = SectionSubject.objects.filter(
        class_name_id=class_id,
        section_id=section_id,
        is_active=True
    ).values_list('subject', flat=True)
    
    return JsonResponse({'subjects': list(subjects)})

@admin_required
def delete_subject(request, subject_id):
    """Delete a subject"""
    if request.method == 'POST':
        try:
            subject = SectionSubject.objects.get(id=subject_id)
            TeacherSubjectAssignment.objects.filter(section_subject=subject).delete()
            subject.delete()
            messages.success(request, 'Subject deleted successfully!')
        except SectionSubject.DoesNotExist:
            messages.error(request, 'Subject not found!')
    return redirect('batch_management')

@admin_required
def update_subject(request, subject_id):
    """Update subject name"""
    if request.method == 'POST':
        try:
            subject = SectionSubject.objects.get(id=subject_id)
            subject.subject = request.POST.get('subject_name')
            subject.save()
            messages.success(request, 'Subject updated successfully!')
        except SectionSubject.DoesNotExist:
            messages.error(request, 'Subject not found!')
    return redirect('batch_management')

@admin_required
def move_class(request, class_id, direction):
    """Move class up or down in order"""
    if request.method == 'POST':
        try:
            classes = list(Class.objects.all().order_by('order', 'id'))
            current_class = Class.objects.get(id=class_id)
            current_index = next(i for i, cls in enumerate(classes) if cls.id == current_class.id)
            
            if direction == 'up' and current_index > 0:
                classes[current_index], classes[current_index - 1] = classes[current_index - 1], classes[current_index]
            elif direction == 'down' and current_index < len(classes) - 1:
                classes[current_index], classes[current_index + 1] = classes[current_index + 1], classes[current_index]
            
            # Update order values
            for i, cls in enumerate(classes):
                cls.order = i
                cls.save()
                
        except (Class.DoesNotExist, StopIteration):
            pass
    return redirect('batch_management')

@admin_required
def toggle_teacher(request, teacher_id):
    """Toggle teacher active status"""
    if request.method == 'POST':
        try:
            teacher = Teacher.objects.get(id=teacher_id)
            teacher.is_active = not teacher.is_active
            teacher.save()
            messages.success(request, f'Teacher {"enabled" if teacher.is_active else "disabled"} successfully!')
        except Teacher.DoesNotExist:
            messages.error(request, 'Teacher not found!')
    return redirect('add_teacher')

@admin_required
def edit_test_session(request, session_id):
    """Edit test session"""
    session = get_object_or_404(TestSession, id=session_id)
    
    if request.method == 'POST':
        session.name = request.POST.get('name')
        session.session_type = request.POST.get('session_type')
        month = request.POST.get('month')
        session.month = month
        session.year = month.split('-')[0] if month else session.year
        session.is_active = 'is_active' in request.POST
        session.save()
        messages.success(request, 'Test session updated successfully!')
        return redirect('test_management')
    
    classes = Class.objects.filter(is_active=True)
    return render(request, 'edit_test_session.html', {
        'session': session,
        'classes': classes
    })

@admin_required
def delete_test_session(request, session_id):
    """Delete test session"""
    session = get_object_or_404(TestSession, id=session_id)
    session.delete()
    messages.success(request, 'Test session deleted successfully!')
    return redirect('test_management')

@admin_required
def select_tests_for_print(request, session_id):
    """Select which tests to include in print"""
    session = get_object_or_404(TestSession, id=session_id)
    
    # For monthly tests, skip selection and go directly to print
    if session.session_type == 'monthly':
        return redirect('print_result_cards', session_id=session_id)
    
    tests = session.tests.all().order_by('test_date', 'test_name')
    
    if request.method == 'POST':
        selected_test_ids = request.POST.getlist('selected_tests')
        if selected_test_ids:
            # Store selected tests in session for print view
            request.session['selected_test_ids'] = selected_test_ids
            return redirect('print_result_cards', session_id=session_id)
        else:
            messages.error(request, 'Please select at least one test to print.')
    
    return render(request, 'select_tests_for_print.html', {
        'session': session,
        'tests': tests
    })

@admin_required
def delete_test(request, test_id):
    """Delete individual test"""
    test = get_object_or_404(Test, id=test_id)
    session_id = test.session.id
    test.delete()
    messages.success(request, 'Test deleted successfully!')
    return redirect('session_detail', session_id=session_id)

@admin_required
def subject_management(request):
    """Manage subjects and teacher assignments"""
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        section_id = request.POST.get('section_id')
        subject_name = request.POST.get('subject_name')
        teacher_id = request.POST.get('teacher_id')
        academic_year = request.POST.get('academic_year')
        
        try:
            # Create SectionSubject
            section_subject = SectionSubject.objects.create(
                class_name_id=class_id,
                section_id=section_id,
                subject=subject_name,
                academic_year=academic_year
            )
            
            # Assign teacher if provided
            if teacher_id:
                TeacherSubjectAssignment.objects.create(
                    teacher_id=teacher_id,
                    section_subject=section_subject
                )
            
            messages.success(request, f'Subject "{subject_name}" added successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        
        return redirect('subject_management')
    
    classes = Class.objects.all()
    teachers = Teacher.objects.all()
    subjects = SectionSubject.objects.select_related('class_name', 'section').prefetch_related('assignments__teacher')
    
    return render(request, 'subject_management.html', {
        'classes': classes,
        'teachers': teachers,
        'subjects': subjects
    })

# Global variable to track message status
message_status_log = []

@admin_required
def get_message_status(request):
    """Get current message sending status from Selenium"""
    global message_status_log
    
    # Return current status
    return JsonResponse({
        'messages': message_status_log,
        'completed': len([m for m in message_status_log if m['status'] == 'sent']) == len(message_status_log)
    })

# -----------------------
# TIMETABLE VIEWS
# -----------------------
@admin_required
def timetable_management(request):
    """Timetable management dashboard"""
    classes = Class.objects.all()
    teachers = Teacher.objects.filter(is_active=True)
    
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        section_id = request.POST.get('section_id')
        subject = request.POST.get('subject')
        teacher_id = request.POST.get('teacher_id')
        day_of_week = request.POST.get('day_of_week')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            Timetable.objects.create(
                class_name_id=class_id,
                section_id=section_id,
                subject=subject,
                teacher_id=teacher_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            messages.success(request, 'Timetable entry added successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        
        return redirect('timetable_management')
    
    timetables = Timetable.objects.select_related('class_name', 'section', 'teacher').filter(is_active=True)
    
    return render(request, 'timetable_management.html', {
        'classes': classes,
        'teachers': teachers,
        'timetables': timetables
    })

@admin_required
def view_timetable(request):
    """View timetable for specific class and section"""
    classes = Class.objects.all()
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    
    timetable_data = None
    selected_class = None
    selected_section = None
    
    if class_id and section_id:
        selected_class = get_object_or_404(Class, id=class_id)
        selected_section = get_object_or_404(Section, id=section_id)
        
        timetables = Timetable.objects.filter(
            class_name_id=class_id,
            section_id=section_id,
            is_active=True
        ).select_related('teacher')
        
        # Organize by day and time
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        timetable_data = {}
        
        for day in days:
            day_schedule = timetables.filter(day_of_week=day).order_by('start_time')
            timetable_data[day] = day_schedule
    
    return render(request, 'view_timetable.html', {
        'classes': classes,
        'timetable_data': timetable_data,
        'selected_class': selected_class,
        'selected_section': selected_section,
        'selected_class_id': class_id,
        'selected_section_id': section_id
    })

@admin_required
def edit_timetable_entry(request, entry_id):
    """Edit timetable entry"""
    entry = get_object_or_404(Timetable, id=entry_id)
    
    if request.method == 'POST':
        entry.subject = request.POST.get('subject')
        entry.teacher_id = request.POST.get('teacher_id')
        entry.start_time = request.POST.get('start_time')
        entry.end_time = request.POST.get('end_time')
        entry.save()
        
        messages.success(request, 'Timetable entry updated successfully!')
        return redirect('timetable_management')
    
    teachers = Teacher.objects.filter(is_active=True)
    return render(request, 'edit_timetable_entry.html', {
        'entry': entry,
        'teachers': teachers
    })

@admin_required
def delete_timetable_entry(request, entry_id):
    """Delete timetable entry"""
    entry = get_object_or_404(Timetable, id=entry_id)
    entry.delete()
    messages.success(request, 'Timetable entry deleted successfully!')
    return redirect('timetable_management')
