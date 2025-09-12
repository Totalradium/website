import json
import threading
from django.http import JsonResponse
from django.shortcuts import render

def send_test_message(request):
    if request.method == 'POST':
        try:
            from .whatsapp_baileys import BaileysWhatsApp
            
            data = json.loads(request.body)
            phone = data.get('phone', '').strip()
            message = data.get('message', '').strip()
            
            if not phone or not message:
                return JsonResponse({'success': False, 'error': 'Phone and message required'})
            
            whatsapp = BaileysWhatsApp()
            
            # Check if WhatsApp is connected
            status = whatsapp.get_status()
            if not status.get('connected'):
                return JsonResponse({'success': False, 'error': 'WhatsApp not connected. Please scan QR code first.'})
            
            # Send message
            result = whatsapp.send_message(phone, message)
            return JsonResponse(result)
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def automate_whatsapp_messages(request):
    if request.method == 'POST':
        try:
            from .whatsapp_baileys import BaileysWhatsApp
            
            data = json.loads(request.body)
            students = data.get('students', [])
            message_template = data.get('message', '')
            
            if not students or not message_template:
                return JsonResponse({'success': False, 'error': 'Students and message required'})
            
            whatsapp = BaileysWhatsApp()
            
            # Check if WhatsApp is connected
            status = whatsapp.get_status()
            if not status.get('connected'):
                return JsonResponse({'success': False, 'error': 'WhatsApp not connected. Please scan QR code first.'})
            
            # Send messages
            sent_count = 0
            failed_count = 0
            
            for student in students:
                phone = student.get('phone', '')
                name = student.get('name', '')
                
                if phone and phone not in ['No Phone', 'Invalid Phone']:
                    # Personalize message
                    message = message_template.replace('{STUDENT_NAME}', name)
                    message = message.replace('{STATUS}', student.get('status', 'absent'))
                    
                    result = whatsapp.send_message(phone, message)
                    if result.get('success'):
                        sent_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
            
            return JsonResponse({
                'success': True, 
                'sent': sent_count, 
                'failed': failed_count,
                'message': f'Sent {sent_count} messages, {failed_count} failed'
            })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})

def get_whatsapp_qr(request):
    """Get QR code for WhatsApp authentication"""
    if request.method == 'GET' and 'application/json' not in request.META.get('HTTP_ACCEPT', ''):
        return render(request, 'whatsapp_qr.html')
    
    from .whatsapp_baileys import BaileysWhatsApp
    
    whatsapp = BaileysWhatsApp()
    result = whatsapp.get_qr_code()
    return JsonResponse(result)

def get_whatsapp_status(request):
    """Get WhatsApp connection status"""
    from .whatsapp_baileys import BaileysWhatsApp
    
    whatsapp = BaileysWhatsApp()
    result = whatsapp.get_status()
    return JsonResponse(result)