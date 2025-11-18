"""Quick development server launcher"""

import os
import sys
from pathlib import Path

# Set development environment
os.environ["USE_DEV_MODE"] = "true"
os.environ["APP_ENV"] = "development"
os.environ["APP_DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"

# Load .env.dev if .env doesn't exist
env_file = Path(".env")
env_dev_file = Path(".env.dev")

if not env_file.exists() and env_dev_file.exists():
    print("📋 Using .env.dev for development")
    import shutil
    shutil.copy(env_dev_file, env_file)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Check OpenAI API key
if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
    print("⚠️  WARNING: OpenAI API key not set!")
    print("   Please edit .env file and add your OPENAI_API_KEY")
    print("   Some features will not work without it.\n")

print("🚀 Starting Octostrator in Development Mode")
print("=" * 50)
print("📍 API Documentation: http://localhost:8000/docs")
print("📍 Health Check: http://localhost:8000/health")
print("📍 WebSocket: ws://localhost:8000/ws/{session_id}")
print("=" * 50)
print("\nPress Ctrl+C to stop the server\n")

# Run the application
import uvicorn

if __name__ == "__main__":
    try:
        uvicorn.run(
            "backend.app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="debug"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)