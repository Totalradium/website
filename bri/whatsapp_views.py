 Baileys'failed': failed_count,
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