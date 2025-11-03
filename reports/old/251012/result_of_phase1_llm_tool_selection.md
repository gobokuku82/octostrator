# Phase 1 완료: LLM 기반 Tool 선택 시스템

**완료일**: 2025-10-08
**Phase**: Phase 1 - LLM 기반 Tool 선택 시스템
**목적**: 하드코딩된 규칙 기반 tool 선택을 LLM 기반으로 전환

---

## ✅ 완료된 작업

### Step 1.1: Config 설정 추가
**파일**: `foundation/config.py`

**변경 사항**:
```python
# 추가된 경로
AGENT_LOGGING_DIR = BASE_DIR / "data" / "system" / "agent_logging"

# 자동 디렉토리 생성
for directory in [CHECKPOINT_DIR, AGENT_LOGGING_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
```

**생성된 디렉토리**:
- `backend/data/system/agent_logging/` (LLM 결정 로그 저장용)

---

### Step 1.2: Tool Selection Prompt 생성
**파일**: `llm_manager/prompts/execution/tool_selection.txt`

**프롬프트 구조**:
1. **상황 정의**: 사용자 질문, 팀 이름, 추출된 키워드
2. **Tool 설명**:
   - legal_search: 법률 정보 검색
   - market_data: 부동산 시세 조회
   - loan_data: 대출 상품 정보
3. **CoT 프로세스**: 4단계 분석 (질문 유형 → 키워드 매칭 → 관계 분석 → 검증)
4. **예시**: 4개의 실제 사용 예시 포함
5. **응답 형식**: JSON (selected_tools, reasoning, execution_order, confidence)

**특징**:
- Chain-of-Thought 기반 의사결정
- 실제 사용 케이스 4개 포함
- 명확한 선택 기준 및 가이드라인

---

### Step 1.3: SearchExecutor에 LLM Tool 선택 로직 추가
**파일**: `execution_agents/search_executor.py`

**추가된 메서드**:

#### 1. `_select_tools_with_llm()`
```python
async def _select_tools_with_llm(
    self,
    query: str,
    keywords: SearchKeywords
) -> Dict[str, Any]:
    """
    LLM을 사용한 tool 선택

    Returns:
        {
            "selected_tools": ["legal", "real_estate", "loan"],
            "reasoning": "...",
            "execution_order": "parallel/sequential/single",
            "confidence": 0.9
        }
    """
```

**특징**:
- LLMService를 통한 비동기 호출
- tool_selection 프롬프트 사용
- 키워드별로 구분하여 전달 (legal_keywords, real_estate_keywords, loan_keywords)
- 실패 시 자동 fallback

#### 2. `_select_tools_with_fallback()`
```python
def _select_tools_with_fallback(self, keywords: SearchKeywords) -> Dict[str, Any]:
    """
    규칙 기반 fallback tool 선택
    LLM 실패 시 사용
    """
```

**특징**:
- 기존 규칙 기반 로직 유지
- LLM 실패 시 안전망 역할
- 동일한 반환 형식 (JSON)

#### 3. `_determine_search_scope()` - Deprecated
- 기존 메서드는 하위 호환성을 위해 유지
- 주석으로 Deprecated 표시
- 향후 제거 예정

---

## 📊 구현 구조

### Before (기존 규칙 기반)
```
사용자 질문 → 키워드 추출 → 규칙 기반 tool 선택 → 실행
                              ❌ 하드코딩
```

### After (LLM 기반)
```
사용자 질문 → 키워드 추출 → LLM tool 선택 → 실행
                              ✅ LLM      ↓
                                     fallback
                                    (규칙 기반)
```

---

## 🔄 LLM Tool 선택 흐름

```
1. prepare_search_node에서 키워드 추출
   ↓
2. _select_tools_with_llm 호출
   ↓
3. LLMService.complete_json_async("tool_selection")
   ↓
4-a. 성공 → LLM 선택 결과 반환
4-b. 실패 → _select_tools_with_fallback으로 안전하게 처리
   ↓
5. selected_tools를 search_scope로 사용
   ↓
6. execute_search_node에서 tool 실행
```

---

## 📁 파일 구조

```
backend/app/service_agent/
├── foundation/
│   └── config.py                         # 수정 - AGENT_LOGGING_DIR 추가
├── execution_agents/
│   └── search_executor.py                # 수정 - LLM tool 선택 추가
├── llm_manager/prompts/execution/
│   └── tool_selection.txt                # 신규 - Tool 선택 프롬프트
└── reports/
    └── result_of_phase1_llm_tool_selection.md  # 본 문서

backend/data/system/
└── agent_logging/                        # 신규 - 자동 생성됨
```

---

## ✨ 주요 개선사항

### 1. 유연한 의사결정
- **기존**: 키워드만 있으면 무조건 해당 tool 실행
- **개선**: LLM이 문맥을 고려하여 필요한 tool만 선택

### 2. 상세한 reasoning
- **기존**: 선택 이유 없음
- **개선**: CoT 기반 4단계 분석 과정 포함

### 3. 실행 순서 명시
- **기존**: 고정된 순서
- **개선**: parallel/sequential/single 명시

### 4. 신뢰도 점수
- **기존**: 없음
- **개선**: confidence 점수로 결정 품질 추적

### 5. 안전한 Fallback
- **기존**: 규칙만 존재
- **개선**: LLM 우선, 실패 시 규칙 기반으로 안전하게 처리

---

## 🎯 예상 효과

1. **더 정확한 Tool 선택**: 문맥을 고려한 LLM 의사결정
2. **불필요한 검색 감소**: 필요한 tool만 실행하여 효율성 증가
3. **추적 가능한 의사결정**: reasoning으로 선택 이유 파악 가능
4. **데이터 수집 준비**: Phase 2에서 이 결정들을 DB에 저장 예정

---

## 🔜 다음 단계: Phase 2

Phase 2에서는 이러한 LLM 의사결정 데이터를 저장하는 시스템을 구축할 예정:

1. DecisionLogger 클래스 생성
2. DB 스키마 설계 및 구현
3. Planning Agent에 로깅 통합
4. Search Executor에 로깅 통합
5. 실행 결과 업데이트

---

## 📝 참고사항

- 기존 코드의 동작은 변경되지 않음 (하위 호환성 유지)
- LLM 실패 시 자동으로 기존 규칙 기반으로 동작
- 테스트는 별도로 관리 (실제 코드에 포함하지 않음)
- 모든 경로는 Config를 통해 설정 (하드코딩 없음)

---

**작성자**: Claude Code
**버전**: 1.0
**상태**: Phase 1 완료 ✅