'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Message, TodoItem, InterruptData, WebSocketMessage } from '@/types'

export function useWebSocket() {
  const [messages, setMessages] = useState<Message[]>([])
  const [todos, setTodos] = useState<TodoItem[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [interruptData, setInterruptData] = useState<InterruptData | null>(null)
  const [sessionId, setSessionId] = useState<string>('')

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    // Generate session ID if not exists
    const sid = sessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    if (!sessionId) setSessionId(sid)

    // Connect to WebSocket
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sid}`)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const wsMessage: WebSocketMessage = JSON.parse(event.data)

        switch (wsMessage.type) {
          case 'response':
            // Add assistant message
            const assistantMessage: Message = {
              id: `msg_${Date.now()}`,
              role: 'assistant',
              content: wsMessage.data.content || wsMessage.data.message || JSON.stringify(wsMessage.data),
              timestamp: new Date(),
              metadata: wsMessage.data.metadata
            }
            setMessages(prev => [...prev, assistantMessage])
            break

          case 'todo_update':
            // Update todos
            if (wsMessage.data.todos) {
              const newTodos: TodoItem[] = wsMessage.data.todos.map((t: any) => ({
                ...t,
                created_at: new Date(t.created_at),
                updated_at: new Date(t.updated_at)
              }))
              setTodos(newTodos)
            }
            break

          case 'interrupt':
            // Handle interrupt
            setInterruptData(wsMessage.data as InterruptData)
            break

          default:
            console.log('Unknown message type:', wsMessage.type)
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      wsRef.current = null

      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Attempting to reconnect...')
        connect()
      }, 3000)
    }

    wsRef.current = ws
  }, [sessionId])

  // Connect on mount
  useEffect(() => {
    connect()

    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connect])

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected')
      return
    }

    // Add user message to UI
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])

    // Send to backend
    const wsMessage: WebSocketMessage = {
      type: 'query',
      data: {
        query: content,
        context: {
          current_todos: todos
        }
      },
      session_id: sessionId
    }

    wsRef.current.send(JSON.stringify(wsMessage))
  }, [sessionId, todos])

  const handleInterrupt = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return
    }

    const wsMessage: WebSocketMessage = {
      type: 'esc_interrupt',
      data: {},
      session_id: sessionId
    }

    wsRef.current.send(JSON.stringify(wsMessage))
    setInterruptData(null)
  }, [sessionId])

  const resumeFromInterrupt = useCallback((response: any) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return
    }

    const wsMessage: WebSocketMessage = {
      type: 'resume',
      data: {
        value: response
      },
      session_id: sessionId
    }

    wsRef.current.send(JSON.stringify(wsMessage))
    setInterruptData(null)
  }, [sessionId])

  const editTodo = useCallback((command: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return
    }

    const wsMessage: WebSocketMessage = {
      type: 'edit_todo',
      data: {
        command
      },
      session_id: sessionId
    }

    wsRef.current.send(JSON.stringify(wsMessage))
  }, [sessionId])

  return {
    messages,
    todos,
    isConnected,
    interruptData,
    sendMessage,
    handleInterrupt,
    resumeFromInterrupt,
    editTodo
  }
}
