from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from .models import Student, Attendance, AttendanceNotification
from .whatsapp_views import send_attendance_notification
import json
import threading

def attendance_notification_log(request):
    """Show students with unsent attendance notifications"""
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
            
            # Send notification in background
            def send_whatsapp():
                from whatsapp_automation import WhatsAppBot
                bot = WhatsAppBot()
                try:
                    if not bot.is_logged_in():
                        bot.wait_for_qr_scan()
                    
                    success = bot.send_message(phone_str, message)
                    if success:
                        notification.notification_sent = True
                        notification.sent_at = timezone.now()
                        notification.save()
                finally:
                    bot.close()
            
            thread = threading.Thread(target=send_whatsapp)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'success': True, 'message': 'Notification being sent...'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def send_all_notifications(request):
    """Send notifications to all pending students"""
    if request.method == 'POST':
        try:
            pending = AttendanceNotification.objects.filter(notification_sent=False)
            
            def send_bulk_whatsapp():
                from whatsapp_automation import WhatsAppBot
                bot = WhatsAppBot()
                try:
                    if not bot.is_logged_in():
                        bot.wait_for_qr_scan()
                    
                    for notification in pending:
                        student = notification.student
                        attendance = notification.attendance
                        
                        phone = student.guardian_contact1 or student.guardian_contact2
                        if not phone:
                            continue
                        
                        if hasattr(phone, 'as_e164'):
                            phone_str = phone.as_e164
                        else:
                            phone_str = str(phone)
                        
                        status_text = 'Present' if attendance.status == 'P' else 'Absent'
                        message = f"Dear Parent,\n\nYour child {student.std_fname} {student.std_lname} from {student.std_class.class_name}-{student.std_section.std_section if student.std_section else 'N/A'} was {status_text} today ({attendance.date}).\n\nThank you,\nSchool Administration"
                        
                        success = bot.send_message(phone_str, message)
                        if success:
                            notification.notification_sent = True
                            notification.sent_at = timezone.now()
                            notification.save()
                finally:
                    bot.close()
            
            thread = threading.Thread(target=send_bulk_whatsapp)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'success': True, 'message': f'Sending notifications to {pending.count()} students...'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def get_pending_count(request):
    """Get count of pending notifications"""
    count = AttendanceNotification.objects.filter(notification_sent=False).count()
    return JsonResponse({'pending_count': count})