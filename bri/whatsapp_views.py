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
            
            # Format phone number
            if phone.startswith('+92'):
                phone = phone.replace('+92', '92')
            elif phone.startswith('0'):
                phone = '92' + phone[1:]
            elif not phone.startswith('92'):
                phone = '92' + phone
            
            # Create WhatsApp URL and open in Chrome
            import urllib.parse
            import subprocess
            encoded_message = urllib.parse.quote_plus(message)
            whatsapp_url = f'https://web.whatsapp.com/send/?phone={phone}&text={encoded_message}'
            
            try:
                # Auto-send with Selenium
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                import time
                
                def auto_send():
                    driver = None
                    try:
                        options = webdriver.ChromeOptions()
                        # Use a separate profile for WhatsApp automation
                        options.add_argument('--user-data-dir=C:\\temp\\whatsapp_chrome')
                        options.add_argument('--disable-web-security')
                        options.add_argument('--disable-features=VizDisplayCompositor')
                        driver = webdriver.Chrome(options=options)
                        
                        print(f'Opening: {whatsapp_url}')
                        driver.get(whatsapp_url)
                        
                        # Wait for page to load
                        time.sleep(10)
                        print('Waiting for send button...')
                        
                        # Try to send with exact selectors
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
                                print(f'Found {len(elements)} elements with selector: {selector}')
                                if elements:
                                    element = elements[0]
                                    if element.tag_name == 'span':
                                        element = element.find_element(By.XPATH, '..')
                                    
                                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    time.sleep(1)
                                    driver.execute_script("arguments[0].click();", element)
                                    print(f'✅ Message sent using {selector}!')
                                    sent = True
                                    break
                            except Exception as e:
                                print(f'❌ Failed with {selector}: {e}')
                                continue
                        
                        if not sent:
                            print('Trying Enter key as fallback...')
                            try:
                                text_box = driver.find_element(By.CSS_SELECTOR, 'div[contenteditable="true"]')
                                text_box.send_keys(Keys.ENTER)
                                print('✅ Enter key sent!')
                            except Exception as e:
                                print(f'❌ Enter key failed: {e}')
                                print('Could not send - please send manually')
                        
                        time.sleep(5)
                        
                    except Exception as e:
                        print(f'Error: {e}')
                    finally:
                        if driver:
                            driver.quit()
                
                threading.Thread(target=auto_send).start()
                return JsonResponse({'success': True, 'message': 'WhatsApp message sending automatically'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Error: {e}'})
                
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
            
            # Open multiple WhatsApp tabs in Chrome
            import urllib.parse
            import subprocess
            import time
            
            def open_whatsapp_tabs():
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                driver = None
                try:
                    # Initialize single browser instance
                    options = webdriver.ChromeOptions()
                    options.add_argument('--remote-debugging-port=9223')
                    options.add_argument('--user-data-dir=C:\\temp\\whatsapp_automation')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    driver = webdriver.Chrome(options=options)
                    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    wait = WebDriverWait(driver, 30)
                    
                    # Check login status first
                    driver.get('https://web.whatsapp.com')
                    time.sleep(5)
                    
                    if driver.find_elements(By.CSS_SELECTOR, 'canvas[aria-label="Scan me!"]'):
                        print('Please scan QR code to login to WhatsApp Web')
                        try:
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="chat-list"]')))
                            print('Login successful')
                        except:
                            print('Login timeout')
                            return
                    
                    # Send messages to each student
                    for i, student in enumerate(students):
                        if student.get('phone') and student['phone'] not in ['No Phone', 'Invalid Phone']:
                            try:
                                # Format phone number
                                phone = student['phone'].replace('+92', '92').replace('+', '')
                                if phone.startswith('0'):
                                    phone = '92' + phone[1:]
                                elif not phone.startswith('92'):
                                    phone = '92' + phone
                                
                                # Replace template variables
                                message = message_template.replace('{STUDENT_NAME}', student['name'])
                                message = message.replace('{STATUS}', student.get('status', 'absent'))
                                
                                # Create URL
                                encoded_message = urllib.parse.quote_plus(message)
                                whatsapp_url = f'https://web.whatsapp.com/send/?phone={phone}&text={encoded_message}'
                                
                                print(f'Sending to {student["name"]} ({i+1}/{len(students)})')
                                driver.get(whatsapp_url)
                                
                                # Wait for message box
                                try:
                                    message_box = wait.until(EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]')))
                                except:
                                    message_box = wait.until(EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, 'div[contenteditable="true"]')))
                                
                                time.sleep(2)
                                
                                # Send message with exact selectors
                                sent = False
                                selectors = [
                                    'button[data-tab="11"][aria-label="Send"]',
                                    'button.x1c4vz4f.x2lah0s.xdl72j9',
                                    'button[aria-label="Send"]',
                                    'span[data-icon="wds-ic-send-filled"]',
                                    'span[data-icon="send"]'
                                ]
                                
                                for selector in selectors:
                                    try:
                                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                        if elements:
                                            # Try clicking the element or its parent
                                            element = elements[0]
                                            if 'span' in selector:
                                                element = element.find_element(By.XPATH, '..')
                                            
                                            driver.execute_script("arguments[0].click();", element)
                                            sent = True
                                            break
                                    except:
                                        continue
                                
                                if not sent:
                                    try:
                                        message_box.send_keys(Keys.ENTER)
                                    except:
                                        pass
                                
                                print(f'✅ Sent to {student["name"]}')
                                time.sleep(3)  # Delay between messages
                                
                            except Exception as e:
                                print(f'❌ Failed to send to {student["name"]}: {e}')
                                continue
                    
                except Exception as e:
                    print(f'Error in bulk sending: {e}')
                finally:
                    if driver:
                        driver.quit()
            
            # Run in background thread
            thread = threading.Thread(target=open_whatsapp_tabs)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'success': True, 'message': f'Opening {len(students)} WhatsApp tabs in Chrome'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'error': 'Invalid method'})