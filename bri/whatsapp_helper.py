"""
WhatsApp automation helper functions with improved error handling
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse

class WhatsAppSender:
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Setup Chrome driver with proper options"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--user-data-dir=C:\\Users\\A_R\\AppData\\Local\\Google\\Chrome\\User Data')
            options.add_argument('--profile-directory=Default')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)
            return True
        except Exception as e:
            print(f"Error setting up driver: {e}")
            return False
    
    def check_login(self):
        """Check if user is logged into WhatsApp Web"""
        try:
            self.driver.get('https://web.whatsapp.com')
            time.sleep(5)
            
            # Check for QR code
            if self.driver.find_elements(By.CSS_SELECTOR, 'canvas[aria-label="Scan me!"]'):
                print('Please scan QR code to login to WhatsApp Web')
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="chat-list"]')))
                    print('Login successful')
                    return True
                except:
                    print('Login timeout')
                    return False
            else:
                print('Already logged in')
                return True
        except Exception as e:
            print(f"Error checking login: {e}")
            return False
    
    def send_single_message(self, phone, message):
        """Send a single message"""
        try:
            # Format phone number
            clean_phone = phone.replace('+92', '92').replace('+', '').replace('-', '').replace(' ', '')
            if clean_phone.startswith('0'):
                clean_phone = '92' + clean_phone[1:]
            elif not clean_phone.startswith('92'):
                clean_phone = '92' + clean_phone
            
            # Create URL
            encoded_message = urllib.parse.quote_plus(message)
            url = f'https://web.whatsapp.com/send/?phone={clean_phone}&text={encoded_message}'
            
            print(f'Sending message to {phone}...')
            self.driver.get(url)
            
            # Wait for message box
            try:
                message_box = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div[contenteditable="true"][data-tab="10"]')))
            except:
                message_box = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div[contenteditable="true"]')))
            
            time.sleep(2)
            
            # Try to send
            sent = False
            send_selectors = [
                'button[aria-label="Send"]',
                'span[data-icon="send"]',
                'button[data-tab="11"]'
            ]
            
            for selector in send_selectors:
                try:
                    send_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    send_btn.click()
                    sent = True
                    break
                except:
                    continue
            
            if not sent:
                message_box.send_keys(Keys.ENTER)
            
            print(f'✅ Message sent to {phone}')
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f'❌ Failed to send to {phone}: {e}')
            return False
    
    def send_bulk_messages(self, phone_message_pairs):
        """Send messages to multiple contacts"""
        success_count = 0
        total_count = len(phone_message_pairs)
        
        for i, (phone, message) in enumerate(phone_message_pairs):
            print(f'Processing {i+1}/{total_count}...')
            if self.send_single_message(phone, message):
                success_count += 1
            time.sleep(2)  # Delay between messages
        
        print(f'Bulk sending completed: {success_count}/{total_count} successful')
        return success_count
    
    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def send_whatsapp_message(phone, message):
    """Helper function to send a single WhatsApp message"""
    sender = WhatsAppSender()
    
    try:
        if not sender.setup_driver():
            return False, "Failed to setup browser"
        
        if not sender.check_login():
            return False, "WhatsApp login required"
        
        success = sender.send_single_message(phone, message)
        return success, "Message sent successfully" if success else "Failed to send message"
        
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        sender.close()

def send_bulk_whatsapp_messages(students, message_template):
    """Helper function to send bulk WhatsApp messages"""
    sender = WhatsAppSender()
    
    try:
        if not sender.setup_driver():
            return 0, "Failed to setup browser"
        
        if not sender.check_login():
            return 0, "WhatsApp login required"
        
        # Prepare phone-message pairs
        phone_message_pairs = []
        for student in students:
            if student.get('phone') and student['phone'] not in ['No Phone', 'Invalid Phone']:
                message = message_template.replace('{STUDENT_NAME}', student['name'])
                message = message.replace('{STATUS}', student.get('status', 'absent'))
                phone_message_pairs.append((student['phone'], message))
        
        success_count = sender.send_bulk_messages(phone_message_pairs)
        return success_count, f"Sent {success_count}/{len(phone_message_pairs)} messages"
        
    except Exception as e:
        return 0, f"Error: {e}"
    finally:
        sender.close()