import sys
from pathlib import Path
backend_dir = Path.cwd() / "backend"
sys.path.insert(0, str(backend_dir))

from app.service_agent.llm_manager.prompt_manager import PromptManager

# 프롬프트 로드 테스트
pm = PromptManager()

try:
    prompt = pm.get("intent_analysis", {"query": "테스트 질문"}, category="cognitive")
    print("✅ intent_analysis 프롬프트 로드 성공!")
    print(f"프롬프트 길이: {len(prompt)} chars")
    
    # JSON 예시 부분 확인
    if "{{" in prompt:
        print("\n⚠️  경고: 프롬프트에 여전히 {{가 남아있습니다 (escape됨)")
        # 이것은 정상입니다 - format() 후에는 {로 변환됨
    
    if "{" in prompt and "query" not in prompt:
        print("\n❌ 에러: 프롬프트에 치환되지 않은 변수가 있습니다!")
        # 첫 100개 { 위치 출력
        positions = [i for i, c in enumerate(prompt) if c == '{'][:10]
        for pos in positions:
            snippet = prompt[max(0, pos-20):min(len(prompt), pos+50)]
            print(f"  위치 {pos}: ...{snippet}...")
    
except Exception as e:
    print(f"❌ 프롬프트 로드 실패: {e}")

