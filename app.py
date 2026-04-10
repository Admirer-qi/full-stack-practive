from flask import Flask, request, jsonify, render_template, session
import json
import os
from datetime import datetime
import requests
# werkzeug.security is now used inside UserRepository

def load_env_file():
    """加载.env文件中的环境变量"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 移除值中的引号
                    if value and value[0] in ('"', "'") and value[-1] == value[0]:
                        value = value[1:-1]
                    os.environ[key] = value
        print(f"OK - Loaded environment variables from {env_path}")
    else:
        print("Info: No .env file found, using system environment variables")

# 加载.env文件
load_env_file()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

# 数据库配置
try:
    from database import init_app as init_database
    from repository import UserRepository, TodoRepository
    init_database(app)
    print("OK - Database initialized")
except ImportError as e:
    print(f"Error importing database modules: {e}")
    print("Make sure Flask-SQLAlchemy and PyMySQL are installed")
    raise

# Enable CORS for all routes
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# In-memory storage for chat histories (user_id -> list of messages)
chat_histories = {}

# Proxy configuration (optional)
PROXY_CONFIG = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
if PROXY_CONFIG:
    print(f"Proxy configuration detected: {PROXY_CONFIG}")
    # Note: Requests will automatically use HTTP_PROXY/HTTPS_PROXY environment variables


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

    # Check if username already exists using repository
    try:
        user = UserRepository.create(username, password)
    except ValueError as e:
        return jsonify({'error': str(e)}), 409
    except Exception as e:
        print(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

    # Log the user in
    session['user_id'] = user.id

    return jsonify({
        'id': user.id,
        'username': user.username
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400

    username = data['username'].strip()
    password = data['password']

    user = UserRepository.authenticate(username, password)
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user.id
    return jsonify({
        'id': user.id,
        'username': user.username
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

    user = UserRepository.get_by_id(user_id)
    if not user:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username
    })

@app.route('/')
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/todos', methods=['GET'])
@login_required
def get_todos():
    user_id = get_current_user_id()

    # 获取用户的待办事项（已经按due_date和created_at排序）
    todos_list = TodoRepository.get_with_tags(user_id)

    # 转换为字典格式
    todos_data = [todo.to_dict() for todo in todos_list]

    return jsonify(todos_data)

@app.route('/api/todos', methods=['POST'])
@login_required
def create_todo():
    user_id = get_current_user_id()
    data = request.get_json()

    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400

    try:
        # 处理due_date格式转换
        due_date = data.get('due_date')
        if due_date:
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid due_date format. Use YYYY-MM-DD'}), 400
        else:
            due_date = None

        # 创建待办事项
        todo = TodoRepository.create(
            user_id=user_id,
            title=data['title'],
            description=data.get('description', ''),
            due_date=due_date,
            tags=data.get('tags', [])
        )

        return jsonify(todo.to_dict()), 201

    except Exception as e:
        print(f"Error creating todo: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/todos/<int:todo_id>', methods=['GET'])
@login_required
def get_todo(todo_id):
    user_id = get_current_user_id()
    todo = TodoRepository.get_by_id(todo_id, user_id)
    if not todo:
        return jsonify({'error': 'Todo not found'}), 404
    return jsonify(todo.to_dict())

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
@login_required
def update_todo(todo_id):
    data = request.get_json()
    user_id = get_current_user_id()

    # 准备更新参数
    update_data = {}

    if 'title' in data:
        update_data['title'] = data['title']
    if 'description' in data:
        update_data['description'] = data['description']
    if 'due_date' in data:
        due_date = data['due_date']
        if due_date:
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid due_date format. Use YYYY-MM-DD'}), 400
        update_data['due_date'] = due_date
    if 'tags' in data:
        update_data['tags'] = data['tags']
    if 'completed' in data:
        update_data['completed'] = data['completed']

    # 更新待办事项
    todo = TodoRepository.update(todo_id, user_id, **update_data)
    if not todo:
        return jsonify({'error': 'Todo not found'}), 404

    return jsonify(todo.to_dict())

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
@login_required
def delete_todo(todo_id):
    user_id = get_current_user_id()

    success = TodoRepository.delete(todo_id, user_id)
    if not success:
        return jsonify({'error': 'Todo not found'}), 404

    return jsonify({'message': 'Todo deleted successfully'}), 200

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    user_id = get_current_user_id()
    stats = TodoRepository.get_stats(user_id)
    return jsonify(stats)

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
    app.run(host="0.0.0.0", port=port, debug=True)
    