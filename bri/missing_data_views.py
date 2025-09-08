from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import Student
from .views import admin_required

@admin_required
def send_missing_data_message(request):
    """Send WhatsApp message about missing data to guardian"""
    if request.method == 'POST':
        import json
        
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            
            student = Student.objects.get(id=student_id)
            
            # Get missing fields
            missing_fields = []
            if not student.guardian_name or student.guardian_name.strip() == '': missing_fields.append('Guardian Name')
            if not student.guardian_contact1 or str(student.guardian_contact1).strip() == '': missing_fields.append('Contact 1')
            if not student.guardian_contact2 or str(student.guardian_contact2).strip() == '': missing_fields.append('Contact 2')
            if not student.address or student.address.strip() == '': missing_fields.append('Address')
            if not student.std_dob or student.std_dob.year == 2000: missing_fields.append('Date of Birth')
            if not student.bform or student.bform.strip() == '': missing_fields.append('B-Form')
            if not hasattr(student, 'profile_picture') or not student.profile_picture: missing_fields.append('Profile Picture')
            
            # Create message
            missing_list = ', '.join(missing_fields)
            message = f"Dear Parent,\n\nWe need to update some information for your child {student.std_fname} {student.std_lname} from {student.std_class.class_name}-{student.std_section.std_section if student.std_section else 'N/A'}.\n\nMissing Information:\n{missing_list}\n\nPlease contact the school office to provide this information.\n\nThank you,\nSchool Administration"
            
            # Use Selenium WhatsApp automation
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            import time
            import threading
            
            def send_whatsapp_message():
                from selenium.webdriver.common.keys import Keys
                
                driver = None
                try:
                    # Format phone number
                    phone = student.guardian_contact1 or student.guardian_contact2
                    phone_str = str(phone).replace('+92', '92').replace('+', '')
                    if phone_str.startswith('0'):
                        phone_str = '92' + phone_str[1:]
                    elif not phone_str.startswith('92'):
                        phone_str = '92' + phone_str
                    
                    # Setup Chrome driver with same options as bulk messaging
                    options = webdriver.ChromeOptions()
                    options.add_argument('--remote-debugging-port=9223')
                    options.add_argument('--user-data-dir=C:\\temp\\whatsapp_automation')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    driver = webdriver.Chrome(options=options)
                    wait = WebDriverWait(driver, 30)
                    
                    # Create URL and navigate
                    import urllib.parse
                    encoded_message = urllib.parse.quote_plus(message)
                    whatsapp_url = f'https://web.whatsapp.com/send/?phone={phone_str}&text={encoded_message}'
                    
                    print(f'Sending missing data message to {student.std_fname} {student.std_lname}')
                    driver.get(whatsapp_url)
                    
                    # Wait for message box
                    try:
                        message_box = wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'div[contenteditable="true"]')))
                    except:
                        print('Message box not found')
                        return
                    
                    time.sleep(3)
                    
                    # Send message using same selectors as bulk messaging
                    selectors = [
                        'button[data-tab="11"]',
                        'button[aria-label="Send"]',
                        'span[data-icon="wds-ic-send-filled"]',
                        'span[data-icon="send"]'
                    ]
                    
                    sent = False
                    for selector in selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                element = elements[0]
                                if element.tag_name == 'span':
                                    element = element.find_element(By.XPATH, '..')
                                
                                driver.execute_script("arguments[0].click();", element)
                                print(f'✅ Missing data message sent using {selector}')
                                sent = True
                                break
                        except:
                            continue
                    
                    if not sent:
                        try:
                            message_box.send_keys(Keys.ENTER)
                            print('✅ Missing data message sent using Enter key')
                        except:
                            print('❌ Could not send missing data message')
                    
                    time.sleep(3)
                    
                except Exception as e:
                    print(f'WhatsApp send error: {e}')
                finally:
                    if driver:
                        driver.quit()
            
            # Send message in background thread
            threading.Thread(target=send_whatsapp_message).start()
            
            return JsonResponse({
                'success': True,
                'message': f'Message sent about missing: {missing_list}'
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})