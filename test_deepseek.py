import os
import requests
import sys

# Use the key from start_app.bat
API_KEY = "sk-f9fc2f31e3984431ae04449ad71e44f1"
print(f"Testing API key: {API_KEY[:8]}...{API_KEY[-4:] if len(API_KEY) > 12 else '***'}")
print(f"Key length: {len(API_KEY)} characters")
print(f"Key starts with 'sk-': {API_KEY.startswith('sk-')}")

url = 'https://api.deepseek.com/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {API_KEY}',
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
        print(f"SUCCESS - API key is valid!")
        print(f"Model: {data.get('model')}")
        print(f"Response: {data['choices'][0]['message']['content']}")
    elif response.status_code == 401:
        print(f"ERROR - Authentication failed (401 Unauthorized)")
        print(f"Response body: {response.text}")
        print("\nPossible issues:")
        print("1. API key is incorrect or expired")
        print("2. API key format is wrong")
        print("3. Account may not be activated")
        print("\nGet a valid API key from: https://platform.deepseek.com/")
    elif response.status_code == 429:
        print(f"WARNING - Rate limit exceeded (429 Too Many Requests)")
        print(f"Response body: {response.text}")
    elif response.status_code == 404:
        print(f"ERROR - Endpoint not found (404)")
        print("Check the API URL is correct")
    else:
        print(f"ERROR - Unexpected response: {response.status_code}")
        print(f"Response body: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"ERROR - Request failed: {e}")
    print("\nCheck your internet connection and try again")
except Exception as e:
    print(f"ERROR: {e}")
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