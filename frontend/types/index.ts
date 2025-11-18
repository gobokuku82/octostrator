export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  metadata?: {
    agent?: string
    execution_time?: number
    status?: string
  }
}

export interface TodoItem {
  id: string
  title: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  priority: 'low' | 'medium' | 'high'
  dependencies?: string[]
  created_at: Date
  updated_at: Date
  metadata?: {
    estimated_time?: number
    agent?: string
    tags?: string[]
  }
}

export interface InterruptData {
  type: 'todo_confirmation' | 'user_input' | 'decision'
  message: string
  todos?: TodoItem[]
  options?: string[]
  context?: any
}

export interface WebSocketMessage {
  type: 'query' | 'response' | 'todo_update' | 'interrupt' | 'resume' | 'edit_todo' | 'esc_interrupt'
  data: any
  session_id?: string
  timestamp?: string
}

export interface SessionState {
  session_id: string
  is_connected: boolean
  is_interrupted: boolean
  current_todos: TodoItem[]
  messages: Message[]
}
