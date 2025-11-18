# Octostrator Frontend

Next.js-based frontend for Octostrator AI Coding Assistant with automatic TODO management.

## Features

- **Real-time Chat Interface**: Chat with the AI assistant in real-time
- **Automatic TODO Management**: TODOs are automatically generated and displayed
- **WebSocket Communication**: Real-time bidirectional communication with backend
- **HITL (Human-in-the-Loop)**: Interactive interrupts for user confirmation
- **Dark Mode Support**: Automatic dark/light mode based on system preferences
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand (via custom hooks)
- **Icons**: Lucide React
- **WebSocket**: Native WebSocket API

## Getting Started

### Prerequisites

- Node.js 20+ (or latest LTS)
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

The application will be available at [http://localhost:3000](http://localhost:3000)

## Project Structure

```
frontend/
├── app/                  # Next.js App Router
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   └── globals.css      # Global styles
├── components/          # React components
│   ├── ChatInterface.tsx     # Main chat UI
│   ├── TodoList.tsx          # TODO list display
│   └── InterruptDialog.tsx   # HITL interrupt dialog
├── hooks/               # Custom React hooks
│   └── useWebSocket.ts  # WebSocket connection hook
├── types/               # TypeScript types
│   └── index.ts         # Shared type definitions
├── lib/                 # Utility functions
│   └── utils.ts         # Helper functions
└── services/            # External services (reserved)
```

## Key Components

### ChatInterface
The main chat interface component that handles user input and displays messages.

**Features**:
- Message history display
- User/Assistant message differentiation
- Connection status indicator
- Send message with Enter key
- Auto-scroll to latest message

### TodoList
Displays the current TODO items with their status and metadata.

**Features**:
- Priority-based color coding
- Status indicators (pending, in_progress, completed, failed)
- Dependency tracking
- Progress statistics
- Tag display

### InterruptDialog
Modal dialog for HITL interactions when the agent needs user input.

**Types**:
- **todo_confirmation**: Confirm TODO items before execution
- **user_input**: Request additional information from user
- **decision**: Choose from multiple options

## WebSocket Integration

The frontend connects to the backend via WebSocket at `ws://localhost:8000/ws/chat/{session_id}`.

### Message Types

**Sent to Backend**:
- `query`: Send user query
- `esc_interrupt`: Cancel current execution (ESC key)
- `resume`: Resume from interrupt with user response
- `edit_todo`: Edit TODO items with natural language

**Received from Backend**:
- `response`: Assistant response
- `todo_update`: Updated TODO list
- `interrupt`: HITL interrupt request

### Session Management
- Automatic session ID generation
- Persistent session across page refreshes (localStorage)
- Automatic reconnection on disconnect

## Usage

### Sending a Query

1. Type your question or request in the input field
2. Press Enter or click Send
3. The assistant will process your request and respond
4. TODOs will be automatically generated and displayed

### Managing TODOs

TODOs are automatically:
- Generated from your requests
- Prioritized based on dependencies
- Executed by appropriate agents
- Updated in real-time

### HITL Interactions

When the agent needs your input:
1. An interrupt dialog will appear
2. Review the information presented
3. Provide your response or confirmation
4. The agent will continue execution

### Keyboard Shortcuts

- `Enter`: Send message
- `Shift + Enter`: New line in message input
- `ESC`: Interrupt current execution (planned)

## Configuration

### Environment Variables

Create a `.env.local` file:

```env
# Backend API URL (default: http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket URL (default: ws://localhost:8000)
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### API Proxy

The frontend proxies API requests to the backend via Next.js rewrites (see `next.config.js`):
- `/api/*` → `http://localhost:8000/api/*`
- `/ws/*` → `http://localhost:8000/ws/*`

## Development

### Running in Development Mode

```bash
npm run dev
```

This starts the Next.js development server with:
- Hot reload
- Fast refresh
- TypeScript checking
- ESLint

### Building for Production

```bash
npm run build
npm start
```

## Troubleshooting

### WebSocket Connection Failed

**Issue**: Cannot connect to WebSocket server

**Solution**:
1. Ensure backend is running on port 8000
2. Check backend logs for errors
3. Verify WebSocket endpoint: `ws://localhost:8000/ws/chat/{session_id}`

### Components Not Rendering

**Issue**: TypeScript errors or missing dependencies

**Solution**:
```bash
# Reinstall dependencies
rm -rf node_modules
npm install

# Clear Next.js cache
rm -rf .next
npm run dev
```

### Styling Issues

**Issue**: Tailwind classes not applying

**Solution**:
1. Check `tailwind.config.js` content paths
2. Ensure `globals.css` imports Tailwind directives
3. Restart dev server

## Future Enhancements

- [ ] File upload for code analysis
- [ ] Export chat history
- [ ] TODO editing via UI (drag & drop)
- [ ] Code syntax highlighting
- [ ] Multiple chat sessions
- [ ] User preferences/settings
- [ ] Notification system
- [ ] Keyboard shortcut customization

## Contributing

This is part of the Octostrator project. See main README for contribution guidelines.

## License

MIT License - See main project LICENSE file
