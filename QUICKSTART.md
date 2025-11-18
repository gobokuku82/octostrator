# Octostrator - Quick Start Guide

Get the Octostrator AI Coding Assistant up and running in 5 minutes!

## Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 20+** (for frontend)
- **UV** (Python package manager) - Install: `pip install uv`
- **OpenAI API Key** (required for LLM functionality)

## Step 1: Clone and Setup Environment

```bash
cd C:\kdy\Projects\Octo_worker\beta_v002

# Create .env file
cp .env.example .env  # or create manually
```

### Configure `.env` file:
```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Development settings (already configured)
USE_DEV_MODE=true
DATABASE_URL=sqlite+aiosqlite:///octostrator.db
REDIS_URL=memory://
SYSTEM_DEBUG=true
```

## Step 2: Install Backend Dependencies

```bash
# Install Python dependencies with UV
uv sync

# This installs:
# - FastAPI
# - LangGraph
# - LangChain
# - OpenAI
# - And all other backend dependencies
```

## Step 3: Install Frontend Dependencies

```bash
cd frontend
npm install

# This installs:
# - Next.js
# - React
# - Tailwind CSS
# - And all other frontend dependencies
```

## Step 4: Start the Backend Server

```bash
# From project root
uv run python run_dev.py

# Server will start on http://localhost:8000
# You should see:
# ✓ "Main graph initialized"
# ✓ "Uvicorn running on http://127.0.0.1:8000"
```

## Step 5: Start the Frontend Server

```bash
# In a new terminal
cd frontend
npm run dev

# Frontend will start on http://localhost:3000
# You should see:
# ✓ "Ready in X.Xs"
# ✓ "Local: http://localhost:3000"
```

## Step 6: Open the Application

1. Open your browser
2. Navigate to: **http://localhost:3000**
3. You should see the Octostrator chat interface!

## Verify Installation

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "app": "Octostrator",
  "version": "1.0.0",
  "environment": "development"
}
```

### Test 2: Integration Tests
```bash
# Make sure both servers are running
uv run python scripts/test_integration.py
```

Expected: 4/5 tests passing (80%)

## Using the Application

### 1. Send a Query

Type in the chat input:
```
"Create a todo list for building a web application"
```

The assistant will:
- Parse your request
- Generate TODOs automatically
- Display them in the right panel
- Execute tasks with appropriate agents

### 2. View TODOs

The right panel shows:
- ✅ Completed tasks (green)
- 🕐 In-progress tasks (blue, animated)
- ⭕ Pending tasks (gray)
- ⚠️ Failed tasks (red)

### 3. Edit TODOs (Natural Language)

Send a message:
```
"Change the first TODO's priority to high"
"Delete the second task"
"Add a new task: Write tests"
```

### 4. HITL Interactions

When the agent needs input, you'll see:
- Modal dialog appears
- Review the request
- Provide your input or decision
- Click "Confirm" to continue

## Common Commands

### Backend
```bash
# Start development server
uv run python run_dev.py

# Run specific tests
uv run python scripts/test_agents.py
uv run python scripts/test_todo_generation.py

# Check database
sqlite3 octostrator.db ".tables"
```

### Frontend
```bash
# Development mode (with hot reload)
npm run dev

# Production build
npm run build
npm start

# Lint code
npm run lint
```

## Troubleshooting

### Issue: "OpenAI API key not found"
**Solution**: Set `OPENAI_API_KEY` in `.env` file

### Issue: "Port 8000 already in use"
**Solution**:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill
```

### Issue: "Cannot connect to WebSocket"
**Solution**:
1. Check backend is running on port 8000
2. Check browser console for errors
3. Verify WebSocket endpoint: `ws://localhost:8000/ws/{session_id}`

### Issue: "Module not found" errors
**Solution**:
```bash
# Backend
uv sync --reinstall

# Frontend
cd frontend
rm -rf node_modules
npm install
```

### Issue: "Next.js won't start"
**Solution**:
```bash
cd frontend
rm -rf .next
npm run dev
```

## Project Structure

```
Octo_worker/beta_v002/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API routes
│   │   └── octostrator/ # Core logic
│   │       ├── agents/  # Domain agents
│   │       └── graphs/  # LangGraph logic
│   └── core/            # Configuration
├── frontend/            # Next.js frontend
│   ├── app/            # Next.js pages
│   ├── components/     # React components
│   ├── hooks/          # Custom hooks
│   └── types/          # TypeScript types
├── scripts/            # Test scripts
├── manual/             # Manual test files
├── .env                # Environment variables
├── pyproject.toml      # Python dependencies
└── run_dev.py          # Quick start script
```

## Key Features

### ✅ Automatic TODO Management
- Generate TODOs from natural language
- Dependency detection
- Priority optimization
- Natural language editing

### ✅ Multi-Agent System
- SearchAgent - Web/database search
- AnalysisAgent - Data analysis
- DocumentAgent - Documentation
- CodeAgent - Code execution

### ✅ Human-in-the-Loop (HITL)
- ESC interrupt (cancel execution)
- interrupt() API (request user input)
- Resume from interrupts

### ✅ Real-time Communication
- WebSocket-based
- Bi-directional updates
- Auto-reconnect

### ✅ Modern UI/UX
- Responsive design
- Dark/light mode
- Priority-based coloring
- Live status updates

## Next Steps

1. **Explore the Interface**
   - Try different queries
   - Observe TODO generation
   - Test agent execution

2. **Read Documentation**
   - `README_OCTOSTRATOR.md` - Project overview
   - `frontend/README.md` - Frontend guide
   - `PHASE_5_SUMMARY.md` - Recent updates

3. **Run Tests**
   - `scripts/test_agents.py` - Agent tests
   - `scripts/test_integration.py` - Full stack tests
   - `scripts/test_todo_generation.py` - TODO logic tests

4. **Customize**
   - Add new agents in `backend/app/octostrator/agents/`
   - Modify prompts in agent files
   - Customize UI in `frontend/components/`

## Support & Resources

- **Issues**: Check logs in terminal
- **Documentation**: See `README_OCTOSTRATOR.md`
- **Architecture**: See `docs/` folder
- **Tests**: See `scripts/` folder

## Development Tips

### Hot Reload
Both frontend and backend support hot reload:
- Backend: Uvicorn auto-reloads on file changes
- Frontend: Next.js Fast Refresh

### Debugging
- **Backend**: Check terminal output with loguru colors
- **Frontend**: Open browser DevTools (F12)
- **WebSocket**: Monitor Network tab → WS connections

### Environment Variables
Create `.env` file with:
```env
OPENAI_API_KEY=sk-...
USE_DEV_MODE=true
SYSTEM_DEBUG=true
LOG_LEVEL=INFO
```

## Quick Reference

### URLs
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health Check: http://localhost:8000/health
- API Docs: http://localhost:8000/docs (Swagger UI)

### Keyboard Shortcuts
- `Enter`: Send message
- `Shift + Enter`: New line
- `ESC`: Interrupt execution (planned)

### Test Commands
```bash
# All tests
uv run python scripts/test_integration.py

# Specific tests
uv run python scripts/test_agents.py
uv run python scripts/test_todo_generation.py
uv run python scripts/test_todo_editing.py
```

---

**You're all set!** 🎉

Open http://localhost:3000 and start coding with your AI assistant!
