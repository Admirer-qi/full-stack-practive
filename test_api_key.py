#!/usr/bin/env python3
"""
Test script to verify DeepSeek API key
"""

import os
import sys

# Try to import requests
try:
    import requests
    requests_available = True
except ImportError:
    requests_available = False
    print("❌ requests module not installed")
    print("   Install with: pip install requests")

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    dotenv_available = True
except ImportError:
    dotenv_available = False
    print("⚠ python-dotenv not installed, using system env vars")

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

if not DEEPSEEK_API_KEY:
    print("❌ No API key found in environment variables")
    print("   Set DEEPSEEK_API_KEY environment variable or create .env file")
    sys.exit(1)

print(f"Testing API key: {DEEPSEEK_API_KEY[:8]}...{DEEPSEEK_API_KEY[-4:] if len(DEEPSEEK_API_KEY) > 12 else '***'}")
print(f"Key length: {len(DEEPSEEK_API_KEY)} characters")

# Check key format
if DEEPSEEK_API_KEY.startswith('sk-'):
    print("⚠ Key starts with 'sk-' (OpenAI format)")
else:
    print("ℹ Key doesn't start with 'sk-'")

# Test the API
url = 'https://api.deepseek.com/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
    'Content-Type': 'application/json'
}

payload = {
    'model': 'deepseek-chat',
    'messages': [
        {
            'role': 'user',
            'content': 'Hello, are you working?'
        }
    ],
    'max_tokens': 50,
    'stream': False
}

print(f"\nTesting API endpoint: {url}")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)

    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ API key is valid!")
        print(f"Model: {data.get('model')}")
        print(f"Response: {data['choices'][0]['message']['content']}")
    elif response.status_code == 401:
        print(f"❌ Authentication failed (401 Unauthorized)")
        print(f"Response body: {response.text}")
        print("\nPossible issues:")
        print("1. API key is incorrect or expired")
        print("2. API key format is wrong")
        print("3. Account may not be activated")
        print("\nGet a valid API key from: https://platform.deepseek.com/")
    elif response.status_code == 429:
        print(f"⚠ Rate limit exceeded (429 Too Many Requests)")
        print(f"Response body: {response.text}")
    elif response.status_code == 404:
        print(f"❌ Endpoint not found (404)")
        print("Check the API URL is correct")
    else:
        print(f"❌ Unexpected response: {response.status_code}")
        print(f"Response body: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")
    print("\nCheck your internet connection and try again")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Troubleshooting Tips:")
print("1. Visit https://platform.deepseek.com/ to get API key")
print("2. Make sure your account is activated")
print("3. Check if you have credits/balance")
print("4. Ensure you're using the correct API endpoint")
print("5. Try a different API key if available")
print("="*60)