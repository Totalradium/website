from django.shortcuts import render
from django.http import JsonResponse
from .models import WhatsAppMessage
from .views import admin_required

@admin_required
def whatsapp_history(request):
    """Show WhatsApp message history"""
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    date_filter = request.GET.get('date', '')
    
    # Base query
    messages = WhatsAppMessage.objects.all().order_by('-created_at')
    
    # Apply filters
    if status_filter != 'all':
        messages = messages.filter(status=status_filter)
    
    if date_filter:
        messages = messages.filter(created_at__date=date_filter)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(messages, 50)  # Show 50 messages per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'whatsapp_history.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter
    })