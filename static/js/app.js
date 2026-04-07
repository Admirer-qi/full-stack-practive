// Todo List Application - Frontend JavaScript

const API_BASE = '/api/todos';
const STATS_API = '/api/stats';

let currentFilter = 'all';
let todos = [];

// DOM Elements
const todoForm = document.getElementById('todo-form');
const titleInput = document.getElementById('title');
const descriptionInput = document.getElementById('description');
const todoList = document.getElementById('todo-list');
const noTodosElement = document.getElementById('no-todos');
const filterButtons = document.querySelectorAll('[data-filter]');
const totalCountEl = document.getElementById('total-count');
const activeCountEl = document.getElementById('active-count');
const completedCountEl = document.getElementById('completed-count');

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    loadTodos();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Form submission
    todoForm.addEventListener('submit', handleAddTodo);

    // Filter buttons
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.getAttribute('data-filter');
            setFilter(filter);
        });
    });
}

// API Functions
async function fetchTodos() {
    try {
        const response = await fetch(API_BASE);
        if (!response.ok) throw new Error('Failed to fetch todos');
        return await response.json();
    } catch (error) {
        console.error('Error fetching todos:', error);
        showAlert('Failed to load todos. Please try again.', 'danger');
        return [];
    }
}

async function fetchStats() {
    try {
        const response = await fetch(STATS_API);
        if (!response.ok) throw new Error('Failed to fetch stats');
        return await response.json();
    } catch (error) {
        console.error('Error fetching stats:', error);
        return { total: 0, active: 0, completed: 0 };
    }
}

async function createTodo(todoData) {
    try {
        const response = await fetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(todoData)
        });

        if (!response.ok) throw new Error('Failed to create todo');
        return await response.json();
    } catch (error) {
        console.error('Error creating todo:', error);
        showAlert('Failed to create todo. Please try again.', 'danger');
        throw error;
    }
}

async function updateTodo(id, updates) {
    try {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });

        if (!response.ok) throw new Error('Failed to update todo');
        return await response.json();
    } catch (error) {
        console.error('Error updating todo:', error);
        showAlert('Failed to update todo. Please try again.', 'danger');
        throw error;
    }
}

async function deleteTodo(id) {
    try {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete todo');
        return await response.json();
    } catch (error) {
        console.error('Error deleting todo:', error);
        showAlert('Failed to delete todo. Please try again.', 'danger');
        throw error;
    }
}

// UI Functions
function loadTodos() {
    fetchTodos().then(data => {
        todos = data;
        updateStats();
        renderTodos();
    });
}

function renderTodos() {
    const filteredTodos = filterTodos(todos);

    if (filteredTodos.length === 0) {
        todoList.innerHTML = '';
        todoList.appendChild(noTodosElement.cloneNode(true));
        noTodosElement.style.display = 'block';
        return;
    }

    noTodosElement.style.display = 'none';
    todoList.innerHTML = '';

    filteredTodos.forEach(todo => {
        const todoElement = createTodoElement(todo);
        todoList.appendChild(todoElement);
    });
}

function createTodoElement(todo) {
    const div = document.createElement('div');
    div.className = `todo-item list-group-item ${todo.completed ? 'completed' : ''}`;
    div.setAttribute('data-id', todo.id);

    const createdAt = new Date(todo.created_at).toLocaleDateString();

    div.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox"
                           ${todo.completed ? 'checked' : ''}
                           id="check-${todo.id}">
                    <label class="form-check-label" for="check-${todo.id}">
                        <h6 class="todo-title mb-1">${escapeHtml(todo.title)}</h6>
                    </label>
                </div>
                ${todo.description ? `<p class="todo-description mb-1">${escapeHtml(todo.description)}</p>` : ''}
                <small class="todo-meta">Created: ${createdAt}</small>
            </div>
            <div class="todo-actions ms-3">
                <button class="btn btn-sm ${todo.completed ? 'btn-outline-warning' : 'btn-outline-success'} toggle-btn"
                        title="${todo.completed ? 'Mark as active' : 'Mark as completed'}">
                    <i class="bi ${todo.completed ? 'bi-arrow-counterclockwise' : 'bi-check'}"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger delete-btn" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;

    // Add event listeners to the buttons
    const checkbox = div.querySelector(`#check-${todo.id}`);
    const toggleBtn = div.querySelector('.toggle-btn');
    const deleteBtn = div.querySelector('.delete-btn');

    checkbox.addEventListener('change', () => toggleTodoCompletion(todo.id, checkbox.checked));
    toggleBtn.addEventListener('click', () => toggleTodoCompletion(todo.id, !todo.completed));
    deleteBtn.addEventListener('click', () => deleteTodoHandler(todo.id));

    return div;
}

function filterTodos(todosList) {
    switch (currentFilter) {
        case 'active':
            return todosList.filter(todo => !todo.completed);
        case 'completed':
            return todosList.filter(todo => todo.completed);
        default:
            return todosList;
    }
}

function setFilter(filter) {
    currentFilter = filter;

    // Update active button state
    filterButtons.forEach(btn => {
        if (btn.getAttribute('data-filter') === filter) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    renderTodos();
}

// Event Handlers
async function handleAddTodo(e) {
    e.preventDefault();

    const title = titleInput.value.trim();
    if (!title) {
        showAlert('Please enter a title for your todo.', 'warning');
        return;
    }

    const todoData = {
        title: title,
        description: descriptionInput.value.trim()
    };

    try {
        await createTodo(todoData);

        // Clear form
        titleInput.value = '';
        descriptionInput.value = '';

        // Reload todos
        loadTodos();
        showAlert('Todo added successfully!', 'success');
    } catch (error) {
        // Error already handled in createTodo
    }
}

async function toggleTodoCompletion(id, completed) {
    try {
        await updateTodo(id, { completed });
        loadTodos();
        showAlert(`Todo marked as ${completed ? 'completed' : 'active'}!`, 'success');
    } catch (error) {
        // Error already handled in updateTodo
    }
}

async function deleteTodoHandler(id) {
    if (!confirm('Are you sure you want to delete this todo?')) {
        return;
    }

    try {
        await deleteTodo(id);
        loadTodos();
        showAlert('Todo deleted successfully!', 'success');
    } catch (error) {
        // Error already handled in deleteTodo
    }
}

// Helper Functions
async function updateStats() {
    const stats = await fetchStats();
    totalCountEl.textContent = stats.total;
    activeCountEl.textContent = stats.active;
    completedCountEl.textContent = stats.completed;
}

function showAlert(message, type) {
    // Remove any existing alerts
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) existingAlert.remove();

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.zIndex = '1050';
    alert.style.minWidth = '300px';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alert);

    // Auto dismiss after 3 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}