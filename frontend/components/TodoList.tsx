'use client'

import { TodoItem } from '@/types'
import { CheckCircle2, Circle, Clock, AlertTriangle, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TodoListProps {
  todos: TodoItem[]
}

export default function TodoList({ todos }: TodoListProps) {
  const getStatusIcon = (status: TodoItem['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'in_progress':
        return <Clock className="w-5 h-5 text-blue-500 animate-pulse" />
      case 'failed':
        return <AlertTriangle className="w-5 h-5 text-red-500" />
      default:
        return <Circle className="w-5 h-5 text-gray-400" />
    }
  }

  const getPriorityColor = (priority: TodoItem['priority']) => {
    switch (priority) {
      case 'high':
        return 'border-red-500 bg-red-50 dark:bg-red-950'
      case 'medium':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950'
      case 'low':
        return 'border-green-500 bg-green-50 dark:bg-green-950'
    }
  }

  const getStatusColor = (status: TodoItem['status']) => {
    switch (status) {
      case 'completed':
        return 'opacity-60'
      case 'in_progress':
        return 'ring-2 ring-blue-500'
      case 'failed':
        return 'opacity-75 bg-red-50 dark:bg-red-950'
      default:
        return ''
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white">
          TODO List
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {todos.length} {todos.length === 1 ? 'task' : 'tasks'}
        </p>
      </div>

      {/* Todo Items */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {todos.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            <div className="text-center">
              <Circle className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm">No tasks yet</p>
              <p className="text-xs mt-2">Tasks will appear here automatically</p>
            </div>
          </div>
        )}

        {todos.map((todo) => (
          <div
            key={todo.id}
            className={cn(
              'border-l-4 rounded-lg p-3 bg-white dark:bg-gray-800 shadow-sm transition-all',
              getPriorityColor(todo.priority),
              getStatusColor(todo.status)
            )}
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">{getStatusIcon(todo.status)}</div>
              <div className="flex-1 min-w-0">
                <h3 className={cn(
                  'font-medium text-gray-900 dark:text-white',
                  todo.status === 'completed' && 'line-through'
                )}>
                  {todo.title}
                </h3>
                {todo.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {todo.description}
                  </p>
                )}

                {/* Metadata */}
                <div className="flex flex-wrap gap-2 mt-2">
                  <span className={cn(
                    'text-xs px-2 py-1 rounded-full font-medium',
                    todo.priority === 'high' && 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
                    todo.priority === 'medium' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
                    todo.priority === 'low' && 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                  )}>
                    {todo.priority}
                  </span>
                  <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                    {todo.status}
                  </span>
                  {todo.metadata?.agent && (
                    <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                      {todo.metadata.agent}
                    </span>
                  )}
                </div>

                {/* Dependencies */}
                {todo.dependencies && todo.dependencies.length > 0 && (
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center gap-1">
                      <ChevronRight className="w-3 h-3" />
                      <span>Depends on {todo.dependencies.length} task(s)</span>
                    </div>
                  </div>
                )}

                {/* Tags */}
                {todo.metadata?.tags && todo.metadata.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {todo.metadata.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="text-xs px-2 py-0.5 rounded bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Stats */}
      {todos.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {todos.filter(t => t.status === 'pending').length}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Pending</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {todos.filter(t => t.status === 'in_progress').length}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">In Progress</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {todos.filter(t => t.status === 'completed').length}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Completed</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
