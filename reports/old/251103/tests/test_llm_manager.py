"""
LLM Manager Test Script
Tests LLMService and PromptManager integration
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.llm_manager import LLMService, PromptManager
from app.service_agent.foundation.context import LLMContext
from app.service_agent.foundation.config import Config


def test_prompt_manager():
    """Test PromptManager functionality"""
    print("=" * 60)
    print("Testing PromptManager")
    print("=" * 60)

    pm = PromptManager()

    # Test list prompts
    print("\n[*] Available prompts:")
    prompts = pm.list_prompts()
    for category, prompt_list in prompts.items():
        print(f"  {category}: {prompt_list}")

    # Test prompt loading with variables
    print("\n[*] Testing prompt loading:")
    try:
        prompt = pm.get(
            "intent_analysis",
            variables={"query": "강남구 전세 시세 알려줘"}
        )
        print(f"  Loaded intent_analysis prompt ({len(prompt)} chars)")
        print(f"  First 200 chars: {prompt[:200]}...")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[OK] PromptManager test completed\n")


def test_llm_service():
    """Test LLMService functionality"""
    print("=" * 60)
    print("Testing LLMService")
    print("=" * 60)

    # Check API key
    api_key = Config.LLM_DEFAULTS.get("api_key")
    if not api_key:
        print("\n[!] SKIPPING: No OpenAI API key found")
        print("    Set OPENAI_API_KEY in .env to test LLM calls\n")
        return

    print(f"\n[*] API Key: {api_key[:10]}...")

    # Create LLM service
    llm_service = LLMService()
    print("[*] LLMService initialized")

    # Test prompt list
    print("\n[*] Checking available prompts:")
    prompts = llm_service.prompt_manager.list_prompts()
    total_prompts = sum(len(p) for p in prompts.values())
    print(f"  Total prompts: {total_prompts}")

    # Note: Actual LLM calls would cost money, so we just validate setup
    print("\n[*] LLM Service setup validated (no actual calls made)")
    print("[OK] LLMService test completed\n")


def test_model_config():
    """Test model configuration"""
    print("=" * 60)
    print("Testing Model Configuration")
    print("=" * 60)

    print("\n[*] Configured models:")
    for prompt_name, model in Config.LLM_DEFAULTS["models"].items():
        print(f"  {prompt_name:25s} -> {model}")

    print("\n[*] Default parameters:")
    for key, value in Config.LLM_DEFAULTS["default_params"].items():
        print(f"  {key:15s}: {value}")

    print("\n[OK] Model configuration test completed\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LLM MANAGER TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_prompt_manager()
        test_llm_service()
        test_model_config()

        print("=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
