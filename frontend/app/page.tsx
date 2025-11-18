'use client'

import ChatInterface from '@/components/ChatInterface'
import TodoList from '@/components/TodoList'
import { useWebSocket } from '@/hooks/useWebSocket'

export default function Home() {
  const { messages, todos, sendMessage, isConnected, interruptData } = useWebSocket()

  return (
    <main className="flex min-h-screen flex-col lg:flex-row bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Chat Interface - Left Side */}
      <div className="flex-1 flex flex-col min-h-screen lg:min-h-0">
        <ChatInterface
          messages={messages}
          onSendMessage={sendMessage}
          isConnected={isConnected}
          interruptData={interruptData}
        />
      </div>

      {/* TODO List - Right Side */}
      <div className="w-full lg:w-96 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <TodoList todos={todos} />
      </div>
    </main>
  )
}
