/**
 * Dream Agent Dashboard - Frontend JavaScript
 * 3-Panel Layout: Progress (Red) | Todo (Yellow) | Chat (Blue)
 *
 * Progress: Todo 작업 진행 상태 (타임라인)
 * Todo: 생성된 Todo 목록 (계획)
 * Chat: 사용자-에이전트 대화
 */

class DreamAgentClient {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.apiBase = window.location.origin;
        this.wsBase = `ws://${window.location.host}`;

        // State
        this.todos = [];

        // DOM Elements
        this.elements = {
            // Chat
            chatMessages: document.getElementById('chatMessages'),
            chatForm: document.getElementById('chatForm'),
            userInput: document.getElementById('userInput'),
            sendBtn: document.getElementById('sendBtn'),
            // Controls
            stopBtn: document.getElementById('stopBtn'),
            clearBtn: document.getElementById('clearBtn'),
            // Status
            connectionStatus: document.getElementById('connectionStatus'),
            sessionBadge: document.getElementById('sessionBadge'),
            // Panels
            progressList: document.getElementById('progressList'),
            progressCount: document.getElementById('progressCount'),
            todoList: document.getElementById('todoList'),
            todoCount: document.getElementById('todoCount'),
        };

        this.init();
    }

    init() {
        // Event listeners
        this.elements.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.elements.stopBtn.addEventListener('click', () => this.stopAgent());
        this.elements.clearBtn.addEventListener('click', () => this.clearAll());

        // Initial state
        this.updateConnectionStatus(false);
    }

    // ========== WebSocket ==========

    connectWebSocket(sessionId) {
        if (this.ws) {
            this.ws.close();
        }

        this.ws = new WebSocket(`${this.wsBase}/ws/${sessionId}`);

        this.ws.onopen = () => {
            console.log('[WS] Connected');
            this.updateConnectionStatus(true);
        };

        this.ws.onclose = () => {
            console.log('[WS] Disconnected');
            this.updateConnectionStatus(false);
        };

        this.ws.onerror = (error) => {
            console.error('[WS] Error:', error);
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleWSMessage(message);
        };

        // Ping every 30s
        this.pingInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }

    handleWSMessage(message) {
        console.log('[WS] Message:', message);

        switch (message.type) {
            case 'todo_update':
                this.handleTodoUpdate(message.data);
                break;

            case 'todos_created':
                this.handleTodosCreated(message.data);
                break;

            case 'complete':
                this.handleComplete(message.data);
                break;

            case 'error':
                this.handleError(message.data);
                break;

            case 'hitl_request':
                this.handleHITLRequest(message.data);
                break;

            case 'pong':
                break;
        }
    }

    // ========== Message Handlers ==========

    // Todo 목록 생성됨 (Planning에서)
    handleTodosCreated(data) {
        if (data.todos) {
            this.todos = data.todos;
        }
        this.renderTodoList();
        this.renderProgressList();
    }

    // 개별 Todo 상태 업데이트 (Execution에서)
    handleTodoUpdate(data) {
        if (data.todos) {
            // 전체 목록 업데이트
            this.todos = data.todos;
        } else if (data.todo) {
            // 단일 Todo 업데이트
            const idx = this.todos.findIndex(t => t.id === data.todo.id);
            if (idx >= 0) {
                this.todos[idx] = data.todo;
            } else {
                this.todos.push(data.todo);
            }
        }

        this.renderTodoList();
        this.renderProgressList();
    }

    handleComplete(data) {
        this.addMessage('assistant', data.response || '작업이 완료되었습니다.');
        this.elements.stopBtn.disabled = true;
        this.elements.sendBtn.disabled = false;

        // 모든 Todo를 완료 상태로 표시
        this.todos.forEach(todo => {
            if (todo.status === 'in_progress' || todo.status === 'pending') {
                todo.status = 'completed';
            }
        });
        this.renderProgressList();
        this.renderTodoList();
    }

    handleError(data) {
        this.addMessage('error', `오류: ${data.error || data.message || '알 수 없는 오류'}`);
        this.elements.stopBtn.disabled = true;
        this.elements.sendBtn.disabled = false;
    }

    handleHITLRequest(data) {
        this.addMessage('system', `[사용자 입력 필요] ${data.message || data.prompt}`);
    }

    // ========== Progress Panel (Todo 진행 상태) ==========

    renderProgressList() {
        const el = this.elements.progressList;

        if (this.todos.length === 0) {
            el.innerHTML = '<p class="empty-state">실행 중인 작업이 없습니다.</p>';
            this.elements.progressCount.textContent = '0';
            return;
        }

        // 완료된 Todo 수 / 전체
        const completedCount = this.todos.filter(t => t.status === 'completed').length;
        const totalCount = this.todos.length;
        this.elements.progressCount.textContent = `${completedCount}/${totalCount}`;

        el.innerHTML = this.todos.map((todo, index) => {
            const statusIcon = this.getStatusIcon(todo.status);
            const statusClass = todo.status;

            return `
                <div class="progress-item ${statusClass}">
                    <span class="progress-icon">${statusIcon}</span>
                    <span class="progress-number">${index + 1}.</span>
                    <span class="progress-task">${this.escapeHtml(todo.task)}</span>
                    ${todo.status === 'in_progress' ? '<span class="loading"></span>' : ''}
                </div>
            `;
        }).join('');
    }

    getStatusIcon(status) {
        switch (status) {
            case 'completed': return '✓';
            case 'in_progress': return '●';
            case 'failed': return '✗';
            case 'blocked': return '⊘';
            case 'skipped': return '−';
            default: return '○'; // pending
        }
    }

    // ========== Todo Panel (Todo 목록 상세) ==========

    renderTodoList() {
        const el = this.elements.todoList;

        this.elements.todoCount.textContent = this.todos.length;

        if (this.todos.length === 0) {
            el.innerHTML = '<p class="empty-state">생성된 Todo가 없습니다.</p>';
            return;
        }

        el.innerHTML = this.todos.map((todo, index) => {
            const tool = todo.metadata?.execution?.tool || '';
            const layer = todo.layer || '';

            return `
                <div class="todo-item ${todo.status}">
                    <div class="todo-header">
                        <span class="todo-number">${index + 1}.</span>
                        <span class="todo-task">${this.escapeHtml(todo.task)}</span>
                    </div>
                    <div class="todo-meta">
                        ${tool ? `<span class="tag tool">${tool}</span>` : ''}
                        ${layer ? `<span class="tag layer">${this.formatLayer(layer)}</span>` : ''}
                        <span class="tag status">${this.getStatusText(todo.status)}</span>
                    </div>
                    ${todo.metadata?.dependency?.depends_on?.length > 0 ?
                        `<div class="todo-deps">의존: ${todo.metadata.dependency.depends_on.join(', ')}</div>` : ''}
                </div>
            `;
        }).join('');
    }

    formatLayer(layer) {
        const layerMap = {
            'ml_execution': 'ML',
            'biz_execution': 'Biz',
            'cognitive': 'Cog',
            'planning': 'Plan',
            'response': 'Res',
        };
        return layerMap[layer] || layer;
    }

    // ========== Chat Panel ==========

    async handleSubmit(e) {
        e.preventDefault();

        const userInput = this.elements.userInput.value.trim();
        if (!userInput) return;

        // Add user message
        this.addMessage('user', userInput);
        this.elements.userInput.value = '';

        // Reset state
        this.todos = [];
        this.renderTodoList();
        this.renderProgressList();

        // Disable input
        this.elements.sendBtn.disabled = true;
        this.elements.stopBtn.disabled = false;

        try {
            await this.runAgent(userInput);
        } catch (error) {
            this.addMessage('error', `연결 오류: ${error.message}`);
            this.elements.sendBtn.disabled = false;
        }
    }

    addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.innerHTML = `<p>${this.formatMessage(content)}</p>`;

        this.elements.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        if (!content) return '';

        let formatted = this.escapeHtml(content);

        // Code blocks
        formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Italic
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    scrollToBottom() {
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }

    // ========== API Calls ==========

    async runAgent(userInput) {
        const response = await fetch(`${this.apiBase}/api/agent/run-async`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_input: userInput,
                language: 'KOR',
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        this.sessionId = data.session_id;
        this.elements.sessionBadge.textContent = `Session: ${this.sessionId.substring(0, 8)}...`;

        // Connect WebSocket
        this.connectWebSocket(this.sessionId);

        return data;
    }

    async stopAgent() {
        if (!this.sessionId) return;

        try {
            await fetch(`${this.apiBase}/api/agent/stop/${this.sessionId}`, {
                method: 'POST',
            });
            this.addMessage('system', '실행이 중지되었습니다.');
            this.elements.stopBtn.disabled = true;
            this.elements.sendBtn.disabled = false;
        } catch (error) {
            console.error('[API] Stop error:', error);
        }
    }

    // ========== Status Updates ==========

    updateConnectionStatus(connected) {
        const el = this.elements.connectionStatus;
        el.textContent = connected ? 'Connected' : 'Disconnected';
        el.className = `status-badge ${connected ? 'connected' : 'disconnected'}`;
    }

    // ========== Utilities ==========

    getStatusText(status) {
        const statusMap = {
            pending: '대기',
            in_progress: '진행중',
            completed: '완료',
            failed: '실패',
            blocked: '차단',
            skipped: '건너뜀',
        };
        return statusMap[status] || status;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    clearAll() {
        // Clear chat
        this.elements.chatMessages.innerHTML = `
            <div class="message system">
                <p>대화가 초기화되었습니다.</p>
            </div>
        `;

        // Clear todos
        this.todos = [];
        this.renderTodoList();
        this.renderProgressList();

        // Reset session
        this.sessionId = null;
        this.elements.sessionBadge.textContent = 'Session: -';
        this.elements.stopBtn.disabled = true;

        // Close WebSocket
        if (this.ws) {
            this.ws.close();
        }

        if (this.pingInterval) {
            clearInterval(this.pingInterval);
        }
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.agentClient = new DreamAgentClient();
});
