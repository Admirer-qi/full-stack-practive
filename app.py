from flask import Flask, request, jsonify, render_template
import json
import os
from datetime import datetime
import requests

# Try to load dotenv for .env file support
try:
    from dotenv import load_dotenv
    dotenv_available = True
except ImportError:
    dotenv_available = False
    print("Warning: python-dotenv not installed. .env files will not be loaded.")
    print("   Install with: pip install python-dotenv")

app = Flask(__name__)

# Load environment variables from .env file if it exists and dotenv is available
if dotenv_available:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"OK - Loaded environment variables from {env_path}")
    else:
        print("Info: No .env file found, using system environment variables")
else:
    print("Info: Using system environment variables (dotenv not available)")

# Enable CORS for all routes
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# In-memory storage for todos
todos = []
next_id = 1

# Proxy configuration (optional)
PROXY_CONFIG = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
if PROXY_CONFIG:
    print(f"Proxy configuration detected: {PROXY_CONFIG}")
    # Note: Requests will automatically use HTTP_PROXY/HTTPS_PROXY environment variables

# Load todos from JSON file if exists
DATA_FILE = 'data/todos.json'

def load_todos():
    global todos, next_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                todos = data.get('todos', [])
                if todos:
                    next_id = max(todo['id'] for todo in todos) + 1
                else:
                    next_id = 1
            print(f"Loaded {len(todos)} todos from {DATA_FILE}")
        except Exception as e:
            print(f"Error loading todos: {e}")
            todos = []
            next_id = 1

def save_todos():
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w') as f:
            json.dump({'todos': todos}, f, indent=2)
        print(f"Saved {len(todos)} todos to {DATA_FILE}")
    except Exception as e:
        print(f"Error saving todos: {e}")

# Load todos on startup
load_todos()

@app.route('/')
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/todos', methods=['GET'])
def get_todos():
    return jsonify(todos)

@app.route('/api/todos', methods=['POST'])
def create_todo():
    global next_id
    data = request.get_json()

    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400

    todo = {
        'id': next_id,
        'title': data['title'],
        'description': data.get('description', ''),
        'completed': False,
        'created_at': datetime.now().isoformat()
    }

    todos.append(todo)
    next_id += 1
    save_todos()

    return jsonify(todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['GET'])
def get_todo(todo_id):
    todo = next((t for t in todos if t['id'] == todo_id), None)
    if todo is None:
        return jsonify({'error': 'Todo not found'}), 404
    return jsonify(todo)

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.get_json()
    todo = next((t for t in todos if t['id'] == todo_id), None)

    if todo is None:
        return jsonify({'error': 'Todo not found'}), 404

    # Update fields if provided
    if 'title' in data:
        todo['title'] = data['title']
    if 'description' in data:
        todo['description'] = data['description']
    if 'completed' in data:
        todo['completed'] = data['completed']

    save_todos()
    return jsonify(todo)

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    global todos
    initial_length = len(todos)
    todos = [t for t in todos if t['id'] != todo_id]

    if len(todos) == initial_length:
        return jsonify({'error': 'Todo not found'}), 404

    save_todos()
    return jsonify({'message': 'Todo deleted successfully'}), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total = len(todos)
    completed = sum(1 for t in todos if t['completed'])
    active = total - completed
    return jsonify({
        'total': total,
        'completed': completed,
        'active': active
    })

# DeepSeek AI Chat API Integration
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
DEEPSEEK_MODEL = "deepseek-chat" 
# Debug info about API key
if DEEPSEEK_API_KEY:
    masked_key = DEEPSEEK_API_KEY[:8] + '...' + DEEPSEEK_API_KEY[-4:] if len(DEEPSEEK_API_KEY) > 12 else '***'
    print(f"OK - DeepSeek API key loaded: {masked_key}")
else:
    print("Warning: DeepSeek API key not found in environment variables")
    print("   Set DEEPSEEK_API_KEY environment variable or create .env file")
    print("   Get API key from: https://platform.deepseek.com/")

@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    """Check AI API configuration status"""
    status = {
        'configured': bool(DEEPSEEK_API_KEY),
        'api_key_masked': None,
        'message': None,
        'key_format': None,
        'key_length': 0
    }

    if DEEPSEEK_API_KEY:
        # Mask the API key for security
        if len(DEEPSEEK_API_KEY) > 12:
            masked_key = DEEPSEEK_API_KEY[:8] + '...' + DEEPSEEK_API_KEY[-4:]
        else:
            masked_key = '***'
        status['api_key_masked'] = masked_key
        status['key_length'] = len(DEEPSEEK_API_KEY)
        status['key_format'] = {
            'starts_with_sk': DEEPSEEK_API_KEY.startswith('sk-'),
            'typical_length': len(DEEPSEEK_API_KEY)
        }

        # Provide format guidance
        if DEEPSEEK_API_KEY.startswith('sk-'):
            status['message'] = 'API key is configured (OpenAI-style format detected)'
            status['format_note'] = 'Your key starts with "sk-". DeepSeek keys typically start with different prefixes.'
        else:
            status['message'] = 'API key is configured'
            status['format_note'] = 'Key format appears non-standard for OpenAI, which may be correct for DeepSeek.'
    else:
        status['message'] = 'API key not configured. Set DEEPSEEK_API_KEY environment variable.'
        status['format_note'] = 'Get API key from: https://platform.deepseek.com/'

    return jsonify(status)

@app.route('/api/ai/test', methods=['GET'])
def test_ai_api():
    print("test_ai_api route loaded")
    """Test the DeepSeek API connection"""
    if not DEEPSEEK_API_KEY:
        return jsonify({'error': 'API key not configured'}), 400

    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {
                    'role': 'user',
                    'content': 'Hello, please respond with just "OK" if you can hear me.'
                }
            ],
            'max_tokens': 10,
            'stream': False
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)

        # 记录详细的请求信息（不包含完整密钥）
        print(f"API Test - Status: {response.status_code}, Key starts with sk-: {DEEPSEEK_API_KEY.startswith('sk-')}")

        result = {
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'key_format_info': {
                'starts_with_sk': DEEPSEEK_API_KEY.startswith('sk-'),
                'length': len(DEEPSEEK_API_KEY)
            }
        }

        if response.status_code == 200:
            data = response.json()
            result['response'] = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            result['model'] = data.get('model', '')
        else:
            # 尝试解析JSON错误信息
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg = error_data['error']
                    if isinstance(error_msg, dict) and 'message' in error_msg:
                        result['error'] = error_msg['message']
                        print(f"API Test Error: {error_msg['message']}")
                    else:
                        result['error'] = str(error_msg)
                        print(f"API Test Error: {error_msg}")
                else:
                    result['error'] = response.text
                    print(f"API Test Raw Error: {response.text[:200]}")
            except:
                result['error'] = response.text
                print(f"API Test Raw Error: {response.text[:200]}")

        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': str(e),
            'success': False,
            'key_format_info': {
                'starts_with_sk': DEEPSEEK_API_KEY.startswith('sk-'),
                'length': len(DEEPSEEK_API_KEY)
            }
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    if not DEEPSEEK_API_KEY:
        return jsonify({'error': 'DeepSeek API key not configured'}), 500

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400

    user_message = data['message']

    # Log the request (without exposing full message in production)
    print(f"AI Chat request: message length={len(user_message)}")

    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant. Please provide clear and concise responses.'
                },
                {
                    'role': 'user',
                    'content': user_message
                }
            ],
            'stream': False
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        ai_response = result['choices'][0]['message']['content']

        return jsonify({
            'response': ai_response,
            'model': result['model']
        })

    except requests.exceptions.RequestException as e:
        # Log detailed error information
        print(f"AI Chat Error: {type(e).__name__}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response Status: {e.response.status_code}")
            print(f"Response Headers: {dict(e.response.headers)}")
            try:
                error_text = e.response.text[:500]
                print(f"Response Body (first 500 chars): {error_text}")
            except:
                pass

        # Provide more specific error messages
        if hasattr(e.response, 'status_code'):
            if e.response.status_code == 401:
                return jsonify({'error': 'API authentication failed. Please check your API key is valid and not expired.'}), 401
            elif e.response.status_code == 429:
                return jsonify({'error': 'API rate limit exceeded. Please try again later.'}), 429
            elif e.response.status_code == 404:
                return jsonify({'error': 'API endpoint not found. Please check the API URL.'}), 404
            else:
                return jsonify({'error': f'API request failed with status {e.response.status_code}: {str(e)}'}), e.response.status_code
        else:
            return jsonify({'error': f'API request failed: {str(e)}'}), 500
    except (KeyError, IndexError) as e:
        return jsonify({'error': f'Invalid API response: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    