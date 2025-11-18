'use client'

import { useState } from 'react'
import { InterruptData } from '@/types'
import { AlertCircle, CheckCircle, XCircle } from 'lucide-react'

interface InterruptDialogProps {
  data: InterruptData
  onResume?: (response: any) => void
  onCancel?: () => void
}

export default function InterruptDialog({ data, onResume, onCancel }: InterruptDialogProps) {
  const [inputValue, setInputValue] = useState('')

  const handleConfirm = () => {
    if (data.type === 'todo_confirmation') {
      onResume?.({ confirmed: true })
    } else if (data.type === 'user_input') {
      onResume?.({ input: inputValue })
    } else if (data.type === 'decision') {
      onResume?.({ decision: inputValue })
    }
  }

  const handleCancel = () => {
    onCancel?.()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
        {/* Header */}
        <div className="border-b border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-blue-500 mt-0.5" />
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                {data.type === 'todo_confirmation' && 'Confirm TODO Items'}
                {data.type === 'user_input' && 'Input Required'}
                {data.type === 'decision' && 'Decision Required'}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {data.message}
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {data.type === 'todo_confirmation' && data.todos && (
            <div className="space-y-3">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                The following tasks will be created:
              </p>
              {data.todos.map((todo, idx) => (
                <div
                  key={idx}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-3"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {idx + 1}.
                    </span>
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {todo.title}
                      </h4>
                      {todo.description && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          {todo.description}
                        </p>
                      )}
                      <div className="flex gap-2 mt-2">
                        <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                          {todo.priority}
                        </span>
                        {todo.dependencies && todo.dependencies.length > 0 && (
                          <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                            {todo.dependencies.length} dependencies
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {data.type === 'user_input' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Your input:
              </label>
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={4}
                placeholder="Enter your response..."
              />
            </div>
          )}

          {data.type === 'decision' && data.options && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Please select an option:
              </p>
              {data.options.map((option, idx) => (
                <button
                  key={idx}
                  onClick={() => setInputValue(option)}
                  className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                    inputValue === option
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-950'
                      : 'border-gray-200 dark:border-gray-700 hover:border-primary-300'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                        inputValue === option
                          ? 'border-primary-500 bg-primary-500'
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                    >
                      {inputValue === option && (
                        <div className="w-2 h-2 bg-white rounded-full" />
                      )}
                    </div>
                    <span className="text-gray-900 dark:text-white">{option}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-6 flex justify-end gap-3">
          <button
            onClick={handleCancel}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <XCircle className="w-4 h-4" />
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={
              (data.type === 'user_input' && !inputValue.trim()) ||
              (data.type === 'decision' && !inputValue)
            }
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2"
          >
            <CheckCircle className="w-4 h-4" />
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}
