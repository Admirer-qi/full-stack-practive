from flask import Flask, request, jsonify, render_template
import json
import os
from datetime import datetime

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)