import json
import threading
from django.http import JsonResponse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from whatsapp_automation import WhatsAppBot

def send_test_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone', '').strip()
            message = data.get('message', '').strip()
            
            if not phone or not message:
                return JsonResponse({'success': False, 'error': 'Phone and message required'})
            
            # Start automation in background thread
            def run_automation():
                bot = WhatsAppBot()
                try:
                    if not bot.is_logged_in():
                        bot.wait_for_qr_scan()
                    
                    bot.send_message(phone, message)
                finally:
                    bot.close()
            
            thread = threading.Thread(target=run_automation)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'success': True, 'message': 'Browser opening... Check for QR code if needed.'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def automate_whatsapp_messages(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            students = data.get('students', [])
            message_template = data.get('message', '')
            
            if not students or not message_template:
                return JsonResponse({'success': False, 'error': 'Students and message required'})
            
            # Start automation in background thread
            def run_automation():
                browser = data.get('browser', 'chrome')
                bot = WhatsAppBot(browser=browser)
                try:
                    if not bot.is_logged_in():
                        bot.wait_for_qr_scan()
                    
                    messages = {}
                    for student in students:
                        if student.get('phone') and student['phone'] not in ['No Phone', 'Invalid Phone']:
                            # Replace template variables
                            message = message_template.replace('{STUDENT_NAME}', student['name'])
                            message = message.replace('{STATUS}', student.get('status', 'absent'))
                            messages[student['phone']] = message
                    
                    bot.send_bulk_messages(messages)
                finally:
                    bot.close()
            
            thread = threading.Thread(target=run_automation)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'success': True, 'message': 'Selenium automation started! Check browser for QR code if needed.'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})