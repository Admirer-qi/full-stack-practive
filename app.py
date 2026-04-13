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

# Chat histories are now stored in database table chat_histories

# Proxy configuration (optional)
PROXY_CONFIG = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
if PROXY_CONFIG:
    print(f"Proxy configuration detected: {PROXY_CONFIG}")
    # Note: Requests will automatically use HTTP_PROXY/HTTPS_PROXY environment variables


def get_current_user_id():
    return session.get('user_id')

def get_chat_history(user_id=None, endpoint='chat'):
    """Get or initialize chat history for a user from database."""
    from repository import ChatHistoryRepository

    if user_id is None:
        user_id = get_current_user_id()

    # If no user_id (not logged in), use session ID as temporary identifier
    if not user_id:
        session_id = session.get('_id', 'anonymous')
        user_key = f'anonymous_{session_id}'
    else:
        user_key = str(user_id)

    # 从数据库获取消息
    messages = ChatHistoryRepository.get_messages_for_ai(user_key, endpoint, max_messages=10)

    # 如果没有消息，添加系统消息
    if not messages:
        current_date = datetime.now().strftime('%B %d, %Y')
        system_content = f"You are a helpful assistant. Context: The current real-world date is {current_date}. When answering questions that involve dates, times, or temporal information, use {current_date} as your reference point. However, DO NOT mention the date unless specifically asked about it. Only provide the date when the user explicitly asks about today's date, the current time, or similar time-related queries. For example, if asked 'what is today's date?' respond with 'Today is {current_date}.' but otherwise don't volunteer date information. Your training data may contain outdated date references - ignore those and use {current_date} when date information is relevant to the question."

        ChatHistoryRepository.add_system_message(user_key, system_content, endpoint)

        # 重新获取消息
        messages = ChatHistoryRepository.get_messages_for_ai(user_key, endpoint, max_messages=10)

    return messages

def clear_chat_history(user_id=None, endpoint=None):
    """Clear chat history for a user from database."""
    from repository import ChatHistoryRepository

    if user_id is None:
        user_id = get_current_user_id()

    if not user_id:
        session_id = session.get('_id', 'anonymous')
        user_key = f'anonymous_{session_id}'
    else:
        user_key = str(user_id)

    # 清除数据库中的历史记录
    deleted_count = ChatHistoryRepository.clear_history(user_key, endpoint)

    # 重新添加系统消息
    current_date = datetime.now().strftime('%B %d, %Y')
    system_content = f"You are a helpful assistant. Context: The current real-world date is {current_date}. When answering questions that involve dates, times, or temporal information, use {current_date} as your reference point. However, DO NOT mention the date unless specifically asked about it. Only provide the date when the user explicitly asks about today's date, the current time, or similar time-related queries. For example, if asked 'what is today's date?' respond with 'Today is {current_date}.' but otherwise don't volunteer date information. Your training data may contain outdated date references - ignore those and use {current_date} when date information is relevant to the question."

    ChatHistoryRepository.add_system_message(user_key, system_content, endpoint or 'chat')

    return deleted_count > 0

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user_id():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def ai_agent_limit(f):
    """
    装饰器：限制AI代理调用速率和每日次数
    要求：用户必须已登录（与login_required一起使用）
    """
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from repository import AiAgentCallRepository

        user_id = get_current_user_id()
        if not user_id:
            # 理论上不会发生，因为login_required会先检查
            return jsonify({'error': 'Authentication required'}), 401

        # 获取客户端IP地址
        ip_address = request.remote_addr

        # 检查限制
        can_call, error_msg = AiAgentCallRepository.can_make_call(
            user_id=user_id,
            ip_address=ip_address,
            rate_limit_per_minute=10,  # 每分钟最多10次
            daily_limit=100  # 每天最多100次
        )

        if not can_call:
            return jsonify({'error': error_msg}), 429

        # 执行被装饰的函数
        try:
            result = f(*args, **kwargs)
            # 如果函数返回的是Flask响应，记录调用
            # 注意：这里假设函数返回的是Flask响应对象或元组
            # 但为了简单，我们直接记录调用
            AiAgentCallRepository.record_call(user_id, ip_address, 'todo_agent')
            return result
        except Exception as e:
            # 即使发生错误也记录调用（因为用户已经消耗了一次调用）
            AiAgentCallRepository.record_call(user_id, ip_address, 'todo_agent')
            raise e

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

    user_message = data['message'].strip()
    clear_history = data.get('clear_history', False)

    # Log the request
    print(f"AI Chat request: message length={len(user_message)}, clear_history={clear_history}")

    try:
        from repository import ChatHistoryRepository

        # 获取用户标识符
        user_id = get_current_user_id()
        if not user_id:
            session_id = session.get('_id', 'anonymous')
            user_key = f'anonymous_{session_id}'
        else:
            user_key = str(user_id)

        # 清除历史（如果需要）
        if clear_history:
            clear_chat_history(user_id, 'chat')

        # 更新系统消息中的日期
        current_date = datetime.now().strftime('%B %d, %Y')
        system_content = f"You are a helpful assistant. Context: The current real-world date is {current_date}. When answering questions that involve dates, times, or temporal information, use {current_date} as your reference point. However, DO NOT mention the date unless specifically asked about it. Only provide the date when the user explicitly asks about today's date, the current time, or similar time-related queries. For example, if asked 'what is today's date?' respond with 'Today is {current_date}.' but otherwise don't volunteer date information. Your training data may contain outdated date references - ignore those and use {current_date} when date information is relevant to the question."

        ChatHistoryRepository.add_system_message(user_key, system_content, 'chat')

        # 添加用户消息到数据库
        ChatHistoryRepository.add_message(user_key, 'user', user_message, 'chat')

        # 获取完整的对话历史（用于AI API）
        history = ChatHistoryRepository.get_messages_for_ai(user_key, 'chat', max_messages=10)

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

        # 添加AI响应到数据库
        ChatHistoryRepository.add_message(user_key, 'assistant', ai_response, 'chat')

        # 获取更新后的历史长度
        history_count = ChatHistoryRepository.get_messages(user_key, 'chat', limit=None)

        return jsonify({
            'response': ai_response,
            'model': result['model'],
            'history_length': len(history_count)
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


# AI Todo Agent
@app.route('/api/ai/todo-agent', methods=['POST'])
@login_required
@ai_agent_limit
def todo_agent():
    """
    AI自动管理待办事项代理
    接收自然语言指令，解析并执行相应的待办事项操作
    """
    from repository import TodoRepository, AiAgentCallRepository

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400

    user_message = data['message'].strip()
    user_id = get_current_user_id()

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    # 检查API密钥是否配置
    if not DEEPSEEK_API_KEY:
        return jsonify({'error': 'DeepSeek API key not configured'}), 500

    # 获取用户现有的待办事项列表，作为上下文提供给AI
    todos = TodoRepository.get_all_by_user(user_id)
    todos_context = [{'id': t.id, 'title': t.title, 'completed': t.completed} for t in todos[:10]]  # 最多10条

    # 构建系统提示词，要求AI返回JSON格式的操作指令
    current_date = datetime.now().strftime('%Y-%m-%d')
    system_prompt = f"""You are an AI assistant that helps manage todo items for a user.
Current date: {current_date}
User ID: {user_id}

The user will give you instructions about managing their todo list. You need to understand their intent and return a JSON object with the following structure:

{{
  "intent": "create_todo|update_todo|delete_todo|list_todos|mark_complete|mark_incomplete|get_todo",
  "parameters": {{
    // 根据意图的不同，参数也不同
  }}
}}

Possible intents and their parameters:
1. create_todo: Create a new todo item.
   Parameters: title (required), description (optional), due_date (optional, format: YYYY-MM-DD), tags (optional array of strings: 'work', 'study', 'life', 'health', 'fitness', 'sports', 'shopping', 'personal', 'urgent', 'important')

2. update_todo: Update an existing todo item.
   Parameters: todo_id (required), title (optional), description (optional), due_date (optional, format: YYYY-MM-DD), tags (optional), completed (optional boolean)

3. delete_todo: Delete a todo item.
   Parameters: todo_id (required)

4. list_todos: List todo items (filtering options).
   Parameters: filter (optional: 'all', 'active', 'completed', 'tag:<tag>'), limit (optional, default 10)

5. mark_complete: Mark a todo item as completed.
   Parameters: todo_id (required)

6. mark_incomplete: Mark a todo item as incomplete (active).
   Parameters: todo_id (required)

7. get_todo: Get details of a specific todo item.
   Parameters: todo_id (required)

Important rules:
- Only operate on the user's own todos (user_id = {user_id}).
- For update/delete/mark operations, you must verify the todo_id belongs to the user.
- If the user asks something not related to todo management, respond with intent "chat" and a "response" parameter with helpful message.
- If the intent is unclear, ask for clarification with intent "clarify" and a "question" parameter.
- Always return valid JSON.

Existing todos (for reference):
{json.dumps(todos_context)}

User's message: "{user_message}"

Respond ONLY with the JSON object, nothing else."""

    try:
        # 调用DeepSeek API
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': DEEPSEEK_MODEL,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            'stream': False,
            'max_tokens': 1000,
            'temperature': 0.1  # 低温度以确保结构化输出
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        ai_response = result['choices'][0]['message']['content']

        # 解析AI返回的JSON
        import json as json_module
        try:
            action = json_module.loads(ai_response.strip())
        except json_module.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {ai_response}")
            return jsonify({
                'error': 'AI returned invalid JSON',
                'raw_response': ai_response[:200]
            }), 500

        intent = action.get('intent')
        parameters = action.get('parameters', {})

        # 根据意图执行相应的操作
        result_data = {'intent': intent, 'parameters': parameters, 'success': True}

        if intent == 'create_todo':
            # 创建待办事项
            title = parameters.get('title')
            if not title:
                return jsonify({'error': 'Title is required for creating todo'}), 400

            due_date = parameters.get('due_date')
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid due_date format. Use YYYY-MM-DD'}), 400

            todo = TodoRepository.create(
                user_id=user_id,
                title=title,
                description=parameters.get('description', ''),
                due_date=due_date,
                tags=parameters.get('tags', [])
            )
            result_data['todo'] = todo.to_dict()
            result_data['message'] = f'Todo created successfully (ID: {todo.id})'

        elif intent == 'update_todo':
            todo_id = parameters.get('todo_id')
            if not todo_id:
                return jsonify({'error': 'todo_id is required for updating todo'}), 400

            # 检查待办事项是否存在且属于当前用户
            todo = TodoRepository.get_by_id(todo_id, user_id)
            if not todo:
                return jsonify({'error': f'Todo not found or access denied (ID: {todo_id})'}), 404

            update_data = {}
            if 'title' in parameters:
                update_data['title'] = parameters['title']
            if 'description' in parameters:
                update_data['description'] = parameters['description']
            if 'due_date' in parameters:
                due_date = parameters['due_date']
                if due_date:
                    try:
                        due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                    except ValueError:
                        return jsonify({'error': 'Invalid due_date format. Use YYYY-MM-DD'}), 400
                update_data['due_date'] = due_date
            if 'tags' in parameters:
                update_data['tags'] = parameters['tags']
            if 'completed' in parameters:
                update_data['completed'] = parameters['completed']

            updated_todo = TodoRepository.update(todo_id, user_id, **update_data)
            if not updated_todo:
                return jsonify({'error': 'Failed to update todo'}), 500

            result_data['todo'] = updated_todo.to_dict()
            result_data['message'] = f'Todo updated successfully (ID: {todo_id})'

        elif intent == 'delete_todo':
            todo_id = parameters.get('todo_id')
            if not todo_id:
                return jsonify({'error': 'todo_id is required for deleting todo'}), 400

            success = TodoRepository.delete(todo_id, user_id)
            if not success:
                return jsonify({'error': f'Todo not found or access denied (ID: {todo_id})'}), 404

            result_data['message'] = f'Todo deleted successfully (ID: {todo_id})'

        elif intent == 'list_todos':
            filter_param = parameters.get('filter', 'all')
            limit = parameters.get('limit', 10)

            todos_list = TodoRepository.get_all_by_user(user_id)
            # 应用过滤
            if filter_param == 'active':
                todos_list = [t for t in todos_list if not t.completed]
            elif filter_param == 'completed':
                todos_list = [t for t in todos_list if t.completed]
            elif filter_param.startswith('tag:'):
                tag = filter_param[4:]
                todos_list = [t for t in todos_list if tag in [tag_obj.tag for tag_obj in t.tags]]
            # 'all' 则不过滤

            # 应用限制
            todos_list = todos_list[:limit]

            result_data['todos'] = [todo.to_dict() for todo in todos_list]
            result_data['count'] = len(todos_list)
            result_data['filter'] = filter_param

        elif intent == 'mark_complete':
            todo_id = parameters.get('todo_id')
            if not todo_id:
                return jsonify({'error': 'todo_id is required for marking todo complete'}), 400

            todo = TodoRepository.get_by_id(todo_id, user_id)
            if not todo:
                return jsonify({'error': f'Todo not found or access denied (ID: {todo_id})'}), 404

            updated_todo = TodoRepository.update(todo_id, user_id, completed=True)
            result_data['todo'] = updated_todo.to_dict()
            result_data['message'] = f'Todo marked as completed (ID: {todo_id})'

        elif intent == 'mark_incomplete':
            todo_id = parameters.get('todo_id')
            if not todo_id:
                return jsonify({'error': 'todo_id is required for marking todo incomplete'}), 400

            todo = TodoRepository.get_by_id(todo_id, user_id)
            if not todo:
                return jsonify({'error': f'Todo not found or access denied (ID: {todo_id})'}), 404

            updated_todo = TodoRepository.update(todo_id, user_id, completed=False)
            result_data['todo'] = updated_todo.to_dict()
            result_data['message'] = f'Todo marked as incomplete (ID: {todo_id})'

        elif intent == 'get_todo':
            todo_id = parameters.get('todo_id')
            if not todo_id:
                return jsonify({'error': 'todo_id is required for getting todo details'}), 400

            todo = TodoRepository.get_by_id(todo_id, user_id)
            if not todo:
                return jsonify({'error': f'Todo not found or access denied (ID: {todo_id})'}), 404

            result_data['todo'] = todo.to_dict()

        elif intent == 'chat':
            # 非待办事项管理的聊天回复
            result_data['response'] = parameters.get('response', 'I can help you manage your todos. Please provide instructions.')
            result_data['message'] = 'Chat response'

        elif intent == 'clarify':
            result_data['question'] = parameters.get('question', 'Could you clarify your request?')
            result_data['message'] = 'Need clarification'

        else:
            return jsonify({'error': f'Unknown intent: {intent}'}), 400

        return jsonify(result_data)

    except requests.exceptions.RequestException as e:
        print(f"AI Todo Agent API Error: {type(e).__name__}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                return jsonify({'error': 'DeepSeek API authentication failed. Check API key.'}), 500
            elif status_code == 429:
                return jsonify({'error': 'DeepSeek API rate limit exceeded. Please try again later.'}), 500
            else:
                return jsonify({'error': f'DeepSeek API request failed: {status_code}'}), 500
        else:
            return jsonify({'error': f'DeepSeek API connection error: {str(e)}'}), 500
    except Exception as e:
        print(f"AI Todo Agent Error: {type(e).__name__}: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
    