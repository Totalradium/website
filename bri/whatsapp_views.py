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
            
            status = whatsapp.get_status()
            if not status.get('connected'):
                return JsonResponse({'success': False, 'error': 'WhatsApp not connected. Please scan QR code first.'})
            
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
            
            status = whatsapp.get_status()
            if not status.get('connected'):
                return JsonResponse({'success': False, 'error': 'WhatsApp not connected. Please scan QR code first.'})
            
            sent_count = 0
            failed_count = 0
            
            for student in students:
                phone = student.get('phone', '')
                name = student.get('name', '')
                
                if phone and phone not in ['No Phone', 'Invalid Phone']:
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

def get_whatsapp_status(request):
    try:
        from .whatsapp_baileys import BaileysWhatsApp
        whatsapp = BaileysWhatsApp()
        status = whatsapp.get_status()
        if not status.get('connected'):
            qr_result = whatsapp.get_qr_code()
            if qr_result.get('qr'):
                status['qr'] = qr_result['qr']
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({"connected": False, "error": str(e)})

def get_whatsapp_qr(request):
    if request.method == 'GET' and 'application/json' not in request.META.get('HTTP_ACCEPT', ''):
        return render(request, 'whatsapp_qr.html')
    
    try:
        from .whatsapp_baileys import BaileysWhatsApp
        whatsapp = BaileysWhatsApp()
        result = whatsapp.get_qr_code()
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": "WhatsApp service not available", "details": str(e)})

def get_message_status(request):
    return JsonResponse({
        'messages': [],
        'completed': True
    })