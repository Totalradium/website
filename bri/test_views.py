import subprocess
import json
import os
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

def test_whatsapp_page(request):
    return render(request, 'test_whatsapp.html')

def test_whatsapp_send(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone', '').strip()
            message = data.get('message', '').strip()
            
            if not phone or not message:
                return JsonResponse({'success': False, 'error': 'Phone and message required'})
            
            test_data = {
                'phone': phone,
                'message': message
            }
            
            temp_file = os.path.join(settings.BASE_DIR, 'temp_test.json')
            with open(temp_file, 'w') as f:
                json.dump(test_data, f)
            
            script_path = os.path.join(settings.BASE_DIR, 'test_bot.js')
            subprocess.Popen(['node', script_path, temp_file], cwd=settings.BASE_DIR)
            
            return JsonResponse({'success': True, 'message': 'Browser opening...'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})