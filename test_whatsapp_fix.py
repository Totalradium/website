#!/usr/bin/env python3
"""
Test script for WhatsApp automation fixes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from whatsapp_automation import WhatsAppBot
import time

def test_single_message():
    """Test sending a single message"""
    print("Testing single message...")
    
    bot = WhatsAppBot()
    
    try:
        # Check if logged in
        if not bot.is_logged_in():
            print("Please scan QR code to login...")
            if not bot.wait_for_qr_scan():
                print("Login failed")
                return False
        
        # Test message (replace with your test number)
        test_phone = "923001234567"  # Replace with actual test number
        test_message = "Test message from updated automation system"
        
        success = bot.send_message(test_phone, test_message)
        
        if success:
            print("✅ Single message test passed")
        else:
            print("❌ Single message test failed")
            
        return success
        
    finally:
        bot.close()

def test_bulk_messages():
    """Test sending bulk messages"""
    print("Testing bulk messages...")
    
    bot = WhatsAppBot()
    
    try:
        # Check if logged in
        if not bot.is_logged_in():
            print("Please scan QR code to login...")
            if not bot.wait_for_qr_scan():
                print("Login failed")
                return False
        
        # Test messages (replace with actual test numbers)
        test_messages = {
            "923001234567": "Test message 1 from bulk automation",
            "923007654321": "Test message 2 from bulk automation"
        }
        
        success_count = bot.send_bulk_messages(test_messages)
        
        if success_count > 0:
            print(f"✅ Bulk message test passed ({success_count} messages sent)")
            return True
        else:
            print("❌ Bulk message test failed")
            return False
            
    finally:
        bot.close()

if __name__ == "__main__":
    print("WhatsApp Automation Test")
    print("=" * 30)
    
    # Test single message
    single_success = test_single_message()
    time.sleep(5)
    
    # Test bulk messages
    bulk_success = test_bulk_messages()
    
    print("\nTest Results:")
    print(f"Single message: {'✅ PASS' if single_success else '❌ FAIL'}")
    print(f"Bulk messages: {'✅ PASS' if bulk_success else '❌ FAIL'}")
    
    if single_success and bulk_success:
        print("\n🎉 All tests passed! WhatsApp automation is working.")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above.")