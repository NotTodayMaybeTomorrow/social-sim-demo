#!/usr/bin/env python3
"""
Check your current Gemini API quota status and test basic functionality.
"""

import google.generativeai as genai
import time
from datetime import datetime
from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

genai.configure(api_key=GEMINI_API_KEY)

def test_single_request():
    """Test a single API request"""
    print("🧪 Testing single API request...")
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content("Hello! Please respond with just 'API Working'")
        print(f"✅ Response: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_rate_limits():
    """Test rate limits with multiple quick requests"""
    print("\n🔍 Testing rate limits with quick consecutive requests...")
    
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    successful_requests = 0
    
    for i in range(5):
        try:
            print(f"Request {i+1}...")
            start_time = time.time()
            response = model.generate_content(f"Count: {i+1}")
            end_time = time.time()
            
            print(f"  ✅ Success in {end_time - start_time:.1f}s")
            successful_requests += 1
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                print("  🚫 Rate limit hit!")
                break
        
        time.sleep(1)  # 1 second between requests
    
    print(f"\nSuccessful requests before limit: {successful_requests}/5")

def check_model_info():
    """Check available models and current model info"""
    print("\n📋 Checking available models...")
    
    try:
        models = genai.list_models()
        print("Available models:")
        for model in models:
            print(f"  - {model.name}")
            if hasattr(model, 'rate_limits'):
                print(f"    Rate limits: {model.rate_limits}")
        
        print(f"\nCurrently using: {GEMINI_MODEL_NAME}")
        
    except Exception as e:
        print(f"❌ Error listing models: {e}")

def suggest_solutions():
    """Suggest solutions based on common issues"""
    print("\n💡 SOLUTIONS FOR RATE LIMIT ISSUES:")
    print("=" * 50)
    
    print("1. 🕒 WAIT IT OUT:")
    print("   - Rate limits reset every hour")
    print("   - Daily quotas reset at midnight UTC")
    print("   - Try again in 1-2 hours")
    
    print("\n2. 🐌 SLOW DOWN:")
    print("   - Use 30-60 second delays between requests")
    print("   - Process in smaller batches (5-10 personas max)")
    
    print("\n3. 🔧 CONFIGURATION:")
    print("   - Set MAX_PERSONAS=5 in your .env file")
    print("   - Try gemini-1.0-pro instead of gemini-1.5-flash")
    
    print("\n4. 🕐 TIMING:")
    print("   - Run during off-peak hours (late night/early morning)")
    print("   - Spread generation across multiple days")
    
    print("\n5. 💰 UPGRADE (if needed):")
    print("   - Consider Gemini Pro API for higher limits")
    print("   - But try free tier solutions first!")

def minimal_test():
    """Run minimal test to check current status"""
    print("\n🔬 Running minimal quota test...")
    
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    
    try:
        # Very simple request
        response = model.generate_content("Hi")
        print("✅ Basic request works - your API key is valid")
        
        # Try a second request after delay
        time.sleep(10)
        response = model.generate_content("Test 2")
        print("✅ Second request works - no immediate rate limit")
        
        print("\n🎯 Your API is working! Rate limits may have reset.")
        
    except Exception as e:
        print(f"❌ Still hitting limits: {e}")
        
        if "429" in str(e):
            print("🚫 Confirmed: You're currently rate limited")
            print("⏰ Wait 1-2 hours before trying again")

if __name__ == "__main__":
    print("🔍 Gemini API Quota Checker")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Run tests
    if test_single_request():
        check_model_info()
        test_rate_limits()
        minimal_test()
    
    suggest_solutions()