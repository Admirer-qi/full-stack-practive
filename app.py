from flask import Flask, request, jsonify, render_template, session
import json
import os
from datetime import datetime
import requests
from werkzeug.security import generate_password_hash, check_password_hash

# Try to load dotenv for .env file support
try:
    from dotenv import load_dotenv
    dotenv_available = True
except ImportError:
    dotenv_available = False
    print("Warning: python-dotenv not installed. .env files will not be loaded.")
    print("   Install with: pip install python-dotenv")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

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
users = []
next_user_id = 1
# In-memory storage for chat histories (user_id -> list of messages)
chat_histories = {}

# Proxy configuration (optional)
PROXY_CONFIG = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
if PROXY_CONFIG:
    print(f"Proxy configuration detected: {PROXY_CONFIG}")
    # Note: Requests will automatically use HTTP_PROXY/HTTPS_PROXY environment variables

# Load todos from JSON file if exists
DATA_FILE = 'data/todos.json'
USERS_FILE = 'data/users.json'

def load_users():
    global users, next_user_id
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                data = json.load(f)
                users = data.get('users', [])
                if users:
                    next_user_id = max(user['id'] for user in users) + 1
                else:
                    next_user_id = 1
            print(f"Loaded {len(users)} users from {USERS_FILE}")
        except Exception as e:
            print(f"Error loading users: {e}")
            users = []
            next_user_id = 1

def save_users():
    try:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, 'w') as f:
            json.dump({'users': users}, f, indent=2)
        print(f"Saved {len(users)} users to {USERS_FILE}")
    except Exception as e:
        print(f"Error saving users: {e}")

def load_todos():
    global todos, next_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                todos = data.get('todos', [])
                # Ensure each todo has a user_id field (default 0 for old todos)
                for todo in todos:
                    if 'user_id' not in todo:
                        todo['user_id'] = 0
                    # Ensure each todo has due_date and tags fields (for backward compatibility)
                    if 'due_date' not in todo:
                        todo['due_date'] = None
                    if 'tags' not in todo:
                        todo['tags'] = []
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
load_users()

def get_current_user_id():
    return session.get('user_id')

def get_chat_history(user_id=None):
    """Get or initialize chat history for a user."""
    if user_id is None:
        user_id = get_current_user_id()

    # If no user_id (not logged in), use session ID as temporary identifier
    if not user_id:
        session_id = session.get('_id', 'anonymous')
        user_key = f'anonymous_{session_id}'
    else:
        user_key = str(user_id)

    if user_key not in chat_histories:
        # Initialize with system message with current date context
        current_date = datetime.now().strftime('%B %d, %Y')
        chat_histories[user_key] = [
            {
                'role': 'system',
                'content': f"You are a helpful assistant. Context: The current real-world date is {current_date}. When answering questions that involve dates, times, or temporal information, use {current_date} as your reference point. However, DO NOT mention the date unless specifically asked about it. Only provide the date when the user explicitly asks about today's date, the current time, or similar time-related queries. For example, if asked 'what is today's date?' respond with 'Today is {current_date}.' but otherwise don't volunteer date information. Your training data may contain outdated date references - ignore those and use {current_date} when date information is relevant to the question."
            }
        ]

    return chat_histories[user_key]

def clear_chat_history(user_id=None):
    """Clear chat history for a user."""
    if user_id is None:
        user_id = get_current_user_id()

    if not user_id:
        session_id = session.get('_id', 'anonymous')
        user_key = f'anonymous_{session_id}'
    else:
        user_key = str(user_id)

    if user_key in chat_histories:
        # Reinitialize with just system message with current date context
        current_date = datetime.now().strftime('%B %d, %Y')
        chat_histories[user_key] = [
            {
                'role': 'system',
                'content': f"You are a helpful assistant. Context: The current real-world date is {current_date}. When answering questions that involve dates, times, or temporal information, use {current_date} as your reference point. However, DO NOT mention the date unless specifically asked about it. Only provide the date when the user explicitly asks about today's date, the current time, or similar time-related queries. For example, if asked 'what is today's date?' respond with 'Today is {current_date}.' but otherwise don't volunteer date information. Your training data may contain outdated date references - ignore those and use {current_date} when date information is relevant to the question."
            }
        ]
        return True
    return False

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user_id():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400

    username = data['username'].strip()
    password = data['password']

    if not username or not password:
        return jsonify({'error': 'Username and password cannot be empty'}), 400

    # Check if username already exists
    if any(user['username'] == username for user in users):
        return jsonify({'error': 'Username already exists'}), 409

    global next_user_id
    user_id = next_user_id
    next_user_id += 1

    user = {
        'id': user_id,
        'username': username,
        'password_hash': generate_password_hash(password)
    }

    users.append(user)
    save_users()

    # Log the user in
    session['user_id'] = user_id

    return jsonify({
        'id': user_id,
        'username': username
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400

    username = data['username'].strip()
    password = data['password']

    user = next((u for u in users if u['username'] == username), None)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user['id']
    return jsonify({
        'id': user['id'],
        'username': user['username']
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/me', methods=['GET'])
def get_current_user():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user['id'],
        'username': user['username']
    })

@app.route('/')
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/todos', methods=['GET'])
@login_required
def get_todos():
    user_id = get_current_user_id()
    user_todos = [t for t in todos if t.get('user_id') == user_id]

    # Sort by due_date (None values last), then by created_at
    def sort_key(todo):
        due_date = todo.get('due_date')
        if due_date is None:
            return ('9999-12-31', todo.get('created_at', ''))
        return (due_date, todo.get('created_at', ''))

    user_todos.sort(key=sort_key)
    return jsonify(user_todos)

@app.route('/api/todos', methods=['POST'])
@login_required
def create_todo():
    global next_id
    user_id = get_current_user_id()
    data = request.get_json()

    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400

    # Validate tags if provided
    tags = data.get('tags', [])
    if tags:
        # Ensure tags are valid (only work, study, life allowed)
        valid_tags = ['work', 'study', 'life']
        tags = [tag for tag in tags if tag in valid_tags]

    todo = {
        'id': next_id,
        'user_id': user_id,
        'title': data['title'],
        'description': data.get('description', ''),
        'due_date': data.get('due_date', None),
        'tags': tags,
        'completed': False,
        'created_at': datetime.now().isoformat()
    }

    todos.append(todo)
    next_id += 1
    save_todos()

    return jsonify(todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['GET'])
@login_required
def get_todo(todo_id):
    user_id = get_current_user_id()
    todo = next((t for t in todos if t['id'] == todo_id and t.get('user_id') == user_id), None)
    if todo is None:
        return jsonify({'error': 'Todo not found'}), 404
    return jsonify(todo)

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
@login_required
def update_todo(todo_id):
    data = request.get_json()
    user_id = get_current_user_id()
    todo = next((t for t in todos if t['id'] == todo_id and t.get('user_id') == user_id), None)

    if todo is None:
        return jsonify({'error': 'Todo not found'}), 404

    # Update fields if provided
    if 'title' in data:
        todo['title'] = data['title']
    if 'description' in data:
        todo['description'] = data['description']
    if 'due_date' in data:
        todo['due_date'] = data['due_date']
    if 'tags' in data:
        # Validate tags
        valid_tags = ['work', 'study', 'life']
        tags = [tag for tag in data['tags'] if tag in valid_tags]
        todo['tags'] = tags
    if 'completed' in data:
        todo['completed'] = data['completed']

    save_todos()
    return jsonify(todo)

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
@login_required
def delete_todo(todo_id):
    global todos
    user_id = get_current_user_id()
    initial_length = len(todos)
    todos = [t for t in todos if not (t['id'] == todo_id and t.get('user_id') == user_id)]

    if len(todos) == initial_length:
        return jsonify({'error': 'Todo not found'}), 404

    save_todos()
    return jsonify({'message': 'Todo deleted successfully'}), 200

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    user_id = get_current_user_id()
    user_todos = [t for t in todos if t.get('user_id') == user_id]
    total = len(user_todos)
    completed = sum(1 for t in user_todos if t['completed'])
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
    clear_history = data.get('clear_history', False)

    # Log the request (without exposing full message in production)
    print(f"AI Chat request: message length={len(user_message)}, clear_history={clear_history}")

    try:
        # Get or clear chat history
        if clear_history:
            clear_chat_history()

        history = get_chat_history()

        # Update system message with current date context
        current_date = datetime.now().strftime('%B %d, %Y')
        if history and history[0]['role'] == 'system':
            # Update the system message with current date context
            history[0]['content'] = f"You are a helpful assistant. Context: The current real-world date is {current_date}. When answering questions that involve dates, times, or temporal information, use {current_date} as your reference point. However, DO NOT mention the date unless specifically asked about it. Only provide the date when the user explicitly asks about today's date, the current time, or similar time-related queries. For example, if asked 'what is today's date?' respond with 'Today is {current_date}.' but otherwise don't volunteer date information. Your training data may contain outdated date references - ignore those and use {current_date} when date information is relevant to the question."

        # Add user message to history
        history.append({'role': 'user', 'content': user_message})

        # Limit history length to avoid token overflow (keep last 10 messages + system message)
        # System message is always at index 0
        if len(history) > 11:  # 1 system message + 10 conversation turns
            # Keep system message and last 10 messages (5 user + 5 assistant pairs ideally)
            history = [history[0]] + history[-10:]

        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': DEEPSEEK_MODEL,
            'messages': history,
            'stream': False,
            'max_tokens': 1000
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        ai_response = result['choices'][0]['message']['content']

        # Add AI response to history
        history.append({'role': 'assistant', 'content': ai_response})

        return jsonify({
            'response': ai_response,
            'model': result['model'],
            'history_length': len(history)
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

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    """Clear the chat history for the current user."""
    try:
        success = clear_chat_history()
        if success:
            return jsonify({'message': 'Chat history cleared successfully'})
        else:
            return jsonify({'message': 'No chat history to clear'})
    except Exception as e:
        print(f"Error clearing chat history: {e}")
        return jsonify({'error': f'Failed to clear chat history: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    