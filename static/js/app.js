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
        if (!response.ok) {
            if (response.status === 401) {
                // Not authenticated
                showAlert('Please login to view your todos', 'warning');
                return [];
            }
            throw new Error('Failed to fetch todos');
        }
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
        if (!response.ok) {
            if (response.status === 401) {
                // Not authenticated
                return { total: 0, active: 0, completed: 0 };
            }
            throw new Error('Failed to fetch stats');
        }
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


function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// AI Chat Functionality
// ============================================

// Chat DOM Elements
let chatForm, messageInput, chatMessages, sendBtn, clearChatBtn, autoScrollCheckbox;

// Chat state
let chatHistory = [];

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    loadTodos();
    setupEventListeners();
    initializeChat();
});

// Initialize chat elements and event listeners
function initializeChat() {
    chatForm = document.getElementById('chat-form');
    messageInput = document.getElementById('message-input');
    chatMessages = document.getElementById('chat-messages');
    sendBtn = document.getElementById('send-btn');
    clearChatBtn = document.getElementById('clear-chat-btn');
    autoScrollCheckbox = document.getElementById('auto-scroll');
    const testConnectionBtn = document.getElementById('test-connection-btn');
    const viewStatusBtn = document.getElementById('view-status-btn');

    if (chatForm) {
        chatForm.addEventListener('submit', handleChatSubmit);
        clearChatBtn.addEventListener('click', clearChat);
        messageInput.addEventListener('input', updateSendButton);
        updateSendButton();

        // Add event listeners for new buttons
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', testAPIConnection);
        }
        if (viewStatusBtn) {
            viewStatusBtn.addEventListener('click', showStatusDetails);
        }

        // Check AI API status
        checkAIStatus();
    }
}

// Check AI API status
async function checkAIStatus() {
    try {
        const statusIndicator = document.getElementById('ai-status-indicator');
        if (!statusIndicator) return;

        const response = await fetch('/api/ai/status');
        if (!response.ok) throw new Error('Failed to check AI status');
        const status = await response.json();

        if (status.configured) {
            statusIndicator.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle"></i>
                    <strong>AI Assistant Ready</strong>
                    <p class="mb-0 small">API key configured (${status.api_key_masked})</p>
                </div>
            `;

            // Enable chat input if previously disabled
            if (messageInput) {
                messageInput.disabled = false;
                messageInput.placeholder = "Type your message here...";
            }
            if (sendBtn) {
                sendBtn.disabled = !messageInput?.value.trim();
            }
        } else {
            statusIndicator.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i>
                    <strong>AI Assistant Not Configured</strong>
                    <p class="mb-0 small">${status.message}</p>
                    <p class="mb-0 small mt-1">
                        <a href="https://platform.deepseek.com/" target="_blank" class="alert-link">
                            Get API key from DeepSeek
                        </a>
                    </p>
                </div>
            `;

            // Disable chat input if not configured
            if (messageInput) {
                messageInput.disabled = true;
                messageInput.placeholder = "Please configure API key first";
            }
            if (sendBtn) {
                sendBtn.disabled = true;
            }
        }
    } catch (error) {
        console.error('Error checking AI status:', error);
        // Show error status
        const statusIndicator = document.getElementById('ai-status-indicator');
        if (statusIndicator) {
            statusIndicator.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-x-circle"></i>
                    <strong>Error Checking AI Status</strong>
                    <p class="mb-0 small">Failed to connect to server. Please refresh the page.</p>
                </div>
            `;
        }
    }
}

// Update send button state based on input
function updateSendButton() {
    if (sendBtn) {
        sendBtn.disabled = !messageInput.value.trim();
    }
}

// Handle chat form submission
async function handleChatSubmit(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    // Clear input
    messageInput.value = '';
    updateSendButton();

    // Add user message to chat
    addMessageToChat('user', message);
    chatHistory.push({ role: 'user', content: message });

    // Show loading indicator
    const loadingId = showLoadingIndicator();

    try {
        // Send to API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        // Remove loading indicator
        removeLoadingIndicator(loadingId);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to get AI response');
        }

        const data = await response.json();

        // Add AI response to chat
        addMessageToChat('ai', data.response);
        chatHistory.push({ role: 'assistant', content: data.response });

        // Show success alert
        showAlert('AI response received!', 'success');
    } catch (error) {
        removeLoadingIndicator(loadingId);
        console.error('Chat error:', error);
        addMessageToChat('ai', `Sorry, I encountered an error: ${error.message}. Please check your API key and try again.`);
        showAlert(`Error: ${error.message}`, 'danger');
    }
}

// Add a message to the chat display
function addMessageToChat(sender, content) {
    if (!chatMessages) return;

    // Remove the "start conversation" placeholder if present
    const placeholder = chatMessages.querySelector('.text-center');
    if (placeholder) {
        placeholder.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const senderLabel = sender === 'user' ? 'You' : 'AI Assistant';

    messageDiv.innerHTML = `
        <div class="chat-message-header">
            <span>${escapeHtml(senderLabel)}</span>
            <span class="chat-message-time">${timestamp}</span>
        </div>
        <div class="chat-message-content">${escapeHtml(content)}</div>
    `;

    chatMessages.appendChild(messageDiv);

    // Auto-scroll if enabled
    if (autoScrollCheckbox.checked) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Show loading indicator
function showLoadingIndicator() {
    if (!chatMessages) return null;

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-loading';
    loadingDiv.id = 'chat-loading-indicator';
    loadingDiv.innerHTML = `
        <div class="spinner-border text-success" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <span>AI is thinking...</span>
    `;

    chatMessages.appendChild(loadingDiv);

    // Auto-scroll if enabled
    if (autoScrollCheckbox.checked) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    return 'chat-loading-indicator';
}

// Remove loading indicator
function removeLoadingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

// Clear chat history
function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history?')) {
        return;
    }

    chatHistory = [];

    if (chatMessages) {
        chatMessages.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="bi bi-chat-quote display-1"></i>
                <h5 class="mt-3">Start a conversation</h5>
                <p>Send a message to begin chatting with the AI assistant.</p>
            </div>
        `;
    }

    showAlert('Chat cleared successfully!', 'success');
}

// Test API connection
async function testAPIConnection() {
    const testConnectionBtn = document.getElementById('test-connection-btn');
    if (testConnectionBtn) {
        testConnectionBtn.disabled = true;
        testConnectionBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Testing...';
    }

    try {
        const response = await fetch('/api/ai/test');
        if (!response.ok) throw new Error('Failed to test API');
        const result = await response.json();

        let alertType = result.success ? 'success' : 'danger';
        let alertMessage = '';

        if (result.success) {
            alertMessage = `
                ✅ API connection successful!
                <br><small>Model: ${result.model || 'Unknown'}</small>
                <br><small>Response: "${result.response || 'No response'}"</small>
            `;
        } else {
            alertMessage = `
                ❌ API connection failed
                <br><small>Status code: ${result.status_code || 'Unknown'}</small>
                <br><small>Key format: ${result.key_format_info?.starts_with_sk ? 'sk- prefix' : 'Non-standard format'}</small>
                <br><small>Error: ${result.error || 'Unknown error'}</small>
            `;

            // Show format warning if key starts with sk-
            if (result.key_format_info?.starts_with_sk) {
                alertMessage += `
                    <div class="mt-2 alert alert-warning p-2">
                        <strong>⚠ Key Format Issue:</strong> Your key starts with "sk-" which is OpenAI format.
                        <br>Get a DeepSeek key from: <a href="https://platform.deepseek.com/" target="_blank">platform.deepseek.com</a>
                    </div>
                `;
            }
        }

        showAlert(alertMessage, alertType);

    } catch (error) {
        console.error('Connection test error:', error);
        showAlert(`❌ Connection test failed: ${error.message}`, 'danger');
    } finally {
        if (testConnectionBtn) {
            testConnectionBtn.disabled = false;
            testConnectionBtn.innerHTML = '<i class="bi bi-plug"></i> Test Connection';
        }
    }
}

// Show detailed status information
function showStatusDetails() {
    fetch('/api/ai/status')
        .then(response => response.json())
        .then(status => {
            let detailsHtml = `
                <div class="status-details">
                    <h6 class="mb-3">API Configuration Details</h6>
                    <table class="table table-sm table-borderless">
                        <tr>
                            <th>Configured:</th>
                            <td>${status.configured ? '✅ Yes' : '❌ No'}</td>
                        </tr>
                        <tr>
                            <th>Key Masked:</th>
                            <td><code>${status.api_key_masked || 'N/A'}</code></td>
                        </tr>
                        <tr>
                            <th>Key Length:</th>
                            <td>${status.key_length || 0} characters</td>
                        </tr>
            `;

            if (status.key_format) {
                detailsHtml += `
                        <tr>
                            <th>Key Format:</th>
                            <td>${status.key_format.starts_with_sk ? '⚠ Starts with "sk-" (OpenAI format)' : '✅ Non-standard format (may be correct)'}</td>
                        </tr>
                `;
            }

            detailsHtml += `
                        <tr>
                            <th>Status:</th>
                            <td>${status.message || 'N/A'}</td>
                        </tr>
                    </table>
            `;

            if (status.format_note) {
                detailsHtml += `<div class="alert alert-info p-2 small mb-0">${status.format_note}</div>`;
            }

            detailsHtml += `
                <div class="mt-3">
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="testAPIConnection()">
                        <i class="bi bi-plug"></i> Test Connection
                    </button>
                </div>
                </div>
            `;

            showAlert(detailsHtml, 'info', false);
        })
        .catch(error => {
            console.error('Status details error:', error);
            showAlert(`Failed to get status details: ${error.message}`, 'danger');
        });
}

// ============================================
// Authentication Functions
// ============================================

let currentUser = null;

async function checkAuth() {
    try {
        const response = await fetch('/api/me');
        if (response.ok) {
            const user = await response.json();
            currentUser = user;
            updateNavbar(user);
            return true;
        } else {
            currentUser = null;
            updateNavbar(null);
            return false;
        }
    } catch (error) {
        console.error('Auth check error:', error);
        currentUser = null;
        updateNavbar(null);
        return false;
    }
}

function updateNavbar(user) {
    const usernameSpan = document.getElementById('navbar-username');
    const dropdownMenu = document.querySelector('#user-menu .dropdown-menu');
    if (!usernameSpan || !dropdownMenu) return;

    if (user) {
        usernameSpan.textContent = user.username;
        // Update dropdown items: hide login/register, show logout
        dropdownMenu.innerHTML = `
            <li><a class="dropdown-item disabled" href="#">Logged in as <strong>${escapeHtml(user.username)}</strong></a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item" href="#" id="logout-btn">Logout</a></li>
        `;
        document.getElementById('logout-btn').addEventListener('click', handleLogout);
    } else {
        usernameSpan.textContent = 'Guest';
        dropdownMenu.innerHTML = `
            <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#loginModal">Login</a></li>
            <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#registerModal">Register</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item disabled" href="#" id="logout-btn">Logout</a></li>
        `;
        // Add event listeners for login/register modal triggers (already handled by Bootstrap)
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        showAlert('Please enter username and password', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            const user = await response.json();
            currentUser = user;
            updateNavbar(user);
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
            if (modal) modal.hide();
            // Clear form
            document.getElementById('login-form').reset();
            showAlert('Login successful!', 'success');
            // Reload todos
            loadTodos();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Login failed', 'danger');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('Login failed: ' + error.message, 'danger');
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-password-confirm').value;

    if (!username || !password) {
        showAlert('Please enter username and password', 'warning');
        return;
    }
    if (password !== confirmPassword) {
        showAlert('Passwords do not match', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (response.ok || response.status === 201) {
            const user = await response.json();
            currentUser = user;
            updateNavbar(user);
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
            if (modal) modal.hide();
            // Clear form
            document.getElementById('register-form').reset();
            showAlert('Registration successful! You are now logged in.', 'success');
            // Reload todos
            loadTodos();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Registration failed', 'danger');
        }
    } catch (error) {
        console.error('Register error:', error);
        showAlert('Registration failed: ' + error.message, 'danger');
    }
}

async function handleLogout(event) {
    if (event) event.preventDefault();
    try {
        const response = await fetch('/api/logout', { method: 'POST' });
        if (response.ok) {
            currentUser = null;
            updateNavbar(null);
            showAlert('Logged out successfully', 'success');
            // Clear todos list
            todos = [];
            renderTodos();
            updateStats();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Logout failed', 'danger');
        }
    } catch (error) {
        console.error('Logout error:', error);
        showAlert('Logout failed: ' + error.message, 'danger');
    }
}

// Initialize authentication when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    // Check auth status
    checkAuth().then(isAuthenticated => {
        if (isAuthenticated) {
            loadTodos();
        }
    });

    // Add event listeners for auth forms
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
});

// Update existing API functions to handle 401 errors
const originalFetchTodos = fetchTodos;
fetchTodos = async function() {
    try {
        const response = await originalFetchTodos();
        return response;
    } catch (error) {
        // If error is 401, user is not authenticated
        if (error.message.includes('401') || error.message.includes('Authentication')) {
            // Notify user to login
            showAlert('Please login to view your todos', 'warning');
            return [];
        }
        throw error;
    }
};

// Update showAlert to optionally allow HTML
function showAlert(message, type, allowHtml = false) {
    // Remove any existing alerts
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) existingAlert.remove();

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.zIndex = '1050';
    alert.style.minWidth = '300px';
    alert.style.maxWidth = '500px';

    if (allowHtml) {
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
    } else {
        alert.innerHTML = `
            ${escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
    }

    document.body.appendChild(alert);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Synchronize navbar with tab system and handle tab changes
document.addEventListener('DOMContentLoaded', () => {
    const navbarLinks = document.querySelectorAll('.navbar-nav .nav-link');
    const tabButtons = document.querySelectorAll('#mainTabs .nav-link');

    navbarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = link.getAttribute('data-tab');
            if (tabId) {
                // Find the corresponding tab button and click it
                tabButtons.forEach(btn => {
                    if (btn.getAttribute('href') === `#${tabId}`) {
                        btn.click();
                    }
                });
            }
        });
    });

    // Add event listener for tab changes to update AI status when AI tab is shown
    const aiTabBtn = document.getElementById('ai-tab-btn');
    if (aiTabBtn) {
        aiTabBtn.addEventListener('shown.bs.tab', function () {
            // Update AI status when AI tab becomes active
            setTimeout(() => {
                checkAIStatus();
            }, 100);
        });
    }

    // Also check AI status when page loads if AI tab is active
    const activeTab = document.querySelector('#mainTabs .nav-link.active');
    if (activeTab && activeTab.getAttribute('href') === '#ai-tab') {
        setTimeout(() => {
            checkAIStatus();
        }, 500);
    }
});