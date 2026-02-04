# Tool Specification (도구 스펙 문서)

> **문서 상태 범례**
> - ✅ 구현 완료
> - ⚠️ 부분 구현 / 검토 필요
> - ❌ 미구현
> - 🔧 사용자 결정 필요

## 1. 개요

Dream Agent의 도구 시스템은 YAML 기반 선언적 정의를 사용합니다.
이 문서는 도구 정의 형식, 검증 규칙, 확장 방법을 설명합니다.

---

## 2. YAML 도구 정의 형식 ✅

### 2.1 실제 사용 구조

> 위치: `tools/definitions/*.yaml`

```yaml
# === 필수 필드 ===
name: sentiment_analyzer          # 고유 식별자 (snake_case)
description: "리뷰 텍스트의 감성을 분석합니다"
tool_type: analysis               # 도구 타입
version: "1.0.0"                  # 시맨틱 버전
layer: ml_execution               # 실행 레이어

executor: ml_agent.sentiment      # 실행자 (executor 이름)

# === 파라미터 정의 ===
parameters:
  - name: reviews
    type: array
    required: true
    description: "분석할 리뷰 텍스트 목록"
  - name: language
    type: string
    required: false
    default: "ko"
    description: "리뷰 언어 (ko, en, ja)"

# === 실행 설정 ===
timeout_sec: 120
max_retries: 3

# === 의존성 ===
dependencies: []                  # 선행 도구 목록
produces:                         # 생성하는 데이터
  - sentiment_results
  - sentiment_summary

# === 메타데이터 ===
tags:
  - sentiment
  - analysis
  - nlp

# === 예시 (선택) ===
examples:
  - input:
      reviews: ["좋아요!", "별로예요"]
    output:
      sentiment_results:
        - text: "좋아요!"
          sentiment: positive
```

### 2.2 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | string | ✅ | 고유 식별자 (snake_case) |
| `description` | string | ✅ | 도구 설명 |
| `tool_type` | string | ✅ | 도구 타입 (analysis, content, ops 등) |
| `version` | string | ✅ | 시맨틱 버전 (x.y.z) |
| `layer` | string | ✅ | 실행 레이어 |
| `executor` | string | ✅ | 실행자 이름 |
| `parameters` | array | ✅ | 파라미터 정의 목록 |
| `timeout_sec` | int | ❌ | 타임아웃 (초) |
| `max_retries` | int | ❌ | 최대 재시도 횟수 |
| `dependencies` | array | ❌ | 선행 도구 목록 |
| `produces` | array | ❌ | 생성 데이터 타입 |
| `tags` | array | ❌ | 검색용 태그 |
| `examples` | array | ❌ | 사용 예시 |

---

## 3. 레이어 정의 ✅

### 3.1 레이어 목록 (실제 사용)

| 레이어 | 설명 | executor 패턴 |
|--------|------|---------------|
| `ml_execution` | ML 분석 작업 | `ml_agent.*` |
| `biz_execution` | 비즈니스 로직 | `biz_agent.*` |
| `collection` | 데이터 수집 | `collector.*` |

### 3.2 레이어 → Executor 매핑

```python
LAYER_TO_EXECUTOR = {
    "collection": "collection_executor",
    "ml_execution": "ml_executor",
    "biz_execution": "biz_executor",
    "analysis": "analysis_executor",
    "insight": "insight_executor",
    "content": "content_executor",
    "report": "report_executor",
    "ops": "ops_executor",
}
```

---

## 4. 현재 정의된 도구 (18개) ✅

### 4.1 Collection Layer

| 도구 | 파일 | 설명 | 상태 |
|------|------|------|------|
| `review_collector` | review_collector.yaml | 리뷰 데이터 수집 | ✅ |
| `preprocessor` | preprocessor.yaml | 데이터 전처리 | ✅ |
| `google_trends` | google_trends.yaml | Google Trends 수집 | ✅ |

### 4.2 Analysis Layer (ML Execution)

| 도구 | 파일 | 설명 | 상태 |
|------|------|------|------|
| `sentiment_analyzer` | sentiment_analyzer.yaml | 감성 분석 | ✅ |
| `keyword_extractor` | keyword_extractor.yaml | 키워드 추출 | ✅ |
| `absa_analyzer` | absa_analyzer.yaml | 속성 기반 감성 분석 | ✅ |
| `problem_classifier` | problem_classifier.yaml | 문제 분류 | ✅ |
| `hashtag_analyzer` | hashtag_analyzer.yaml | 해시태그 분석 | ✅ |
| `competitor_analyzer` | competitor_analyzer.yaml | 경쟁사 분석 | ✅ |

### 4.3 Insight Layer

| 도구 | 파일 | 설명 | 상태 |
|------|------|------|------|
| `insight_generator` | insight_generator.yaml | 인사이트 생성 | ✅ |
| `insight_with_trends` | insight_with_trends.yaml | 트렌드 포함 인사이트 | ✅ |

### 4.4 Content Layer (Biz Execution)

| 도구 | 파일 | 설명 | 상태 |
|------|------|------|------|
| `ad_creative_agent` | ad_creative_agent.yaml | 광고 크리에이티브 | ✅ YAML정의 |
| `storyboard_agent` | storyboard_agent.yaml | 스토리보드 생성 | ✅ YAML정의 |
| `video_agent` | video_agent.yaml | 영상 기획/생성 | ✅ |
| `report_generator` | report_generator.yaml | 리포트 생성 | ✅ |

### 4.5 Ops Layer

| 도구 | 파일 | 설명 | 상태 |
|------|------|------|------|
| `dashboard_agent` | dashboard_agent.yaml | 대시보드 생성 | ✅ YAML정의 |
| `sales_agent` | sales_agent.yaml | 매출 분석 | ✅ YAML정의 |
| `inventory_agent` | inventory_agent.yaml | 재고 관리 | ✅ YAML정의 |

---

## 5. 의존성 그래프 ✅

```
review_collector
    │
    ▼
preprocessor ◄────────────────────── google_trends
    │                                     │
    ├──────────────┬──────────────┐       │
    ▼              ▼              ▼       │
sentiment     keyword        absa         │
_analyzer     _extractor    _analyzer     │
    │              │                      │
    │              ├───► hashtag_analyzer │
    │              │                      │
    └──────┬───────┘                      │
           ▼                              │
    insight_generator ◄───────────────────┘
           │
           ▼
    insight_with_trends
           │
           ▼
    ad_creative_agent
           │
           ▼
    storyboard_agent
           │
           ▼
    video_agent ──────► report_generator
```

---

## 6. 검증 규칙 ✅

### 6.1 필수 필드 검증

```python
REQUIRED_FIELDS = ['name', 'description', 'tool_type', 'version', 'layer', 'executor', 'parameters']
```

### 6.2 의존성 검증

- 모든 의존 도구가 존재해야 함
- 순환 의존성 불허 (ToolValidator.validate_dependencies)
- 자기 자신 의존 불허

### 6.3 파라미터 타입

```yaml
# 지원 타입
type: string | array | object | number | boolean | integer
```

---

## 7. 새 도구 추가 방법 ✅

### Step 1: YAML 파일 생성

```bash
# tools/definitions/my_new_tool.yaml
```

### Step 2: 기본 구조 작성

```yaml
name: my_new_tool
description: "새 도구 설명"
tool_type: analysis
version: "1.0.0"
layer: ml_execution

executor: ml_agent.my_new_tool

parameters:
  - name: input_data
    type: string
    required: true
    description: "입력 데이터"

timeout_sec: 60
max_retries: 3

dependencies:
  - preprocessor

produces:
  - my_result

tags:
  - custom
  - analysis
```

### Step 3: Hot Reload 확인

```python
# 파일 저장 시 자동 로드 (hot_reload.py)
from dream_agent.tools import get_tool_discovery

discovery = get_tool_discovery()
spec = discovery.get("my_new_tool")  # 자동 로드됨
```

### Step 4: 검증

```python
from dream_agent.tools import validate_tool_spec

result = validate_tool_spec(spec)
if not result.valid:
    print(result.errors)
```

---

## 8. Domain Agent 연동 ✅

### 8.1 YAML ↔ Agent 매핑

| YAML 도구 | Domain Agent 파일 | 상태 |
|-----------|-------------------|------|
| sentiment_analyzer | sentiment_analyzer_agent.py | ✅ |
| keyword_extractor | keyword_extractor_agent.py | ✅ |
| hashtag_analyzer | hashtag_analyzer_agent.py | ✅ |
| problem_classifier | problem_classifier_agent.py | ✅ |
| competitor_analyzer | competitor_analyzer_agent.py | ✅ |
| google_trends | google_trends_agent.py | ✅ |
| insight_generator | insight_generator_agent.py | ✅ |
| video_agent | video_agent_graph.py | ✅ |
| report_generator | report_agent_graph.py | ✅ |
| ad_creative_agent | ad_creative_agent_tool.py (16KB) | ✅ |
| storyboard_agent | storyboard_agent_tool.py (15KB) | ✅ |
| dashboard_agent | dashboard_agent_tool.py (14KB) | ✅ |
| sales_agent | sales_material_generator.py (이름 다름) | ⚠️ |
| inventory_agent | __init__.py만 존재 | ❌ |

---

## 🔧 사용자 결정 필요 사항

| 항목 | 설명 | 옵션 |
|------|------|------|
| YAML 스키마 표준화 | `parameters` vs `input_schema` 형식 | 현재 방식 유지 / JSON Schema 전환 |
| 버전 관리 정책 | 도구별 버전 vs 전체 버전 | 개별 관리 / 통합 관리 |
| sales_agent 이름 통일 | YAML명과 Agent 파일명 불일치 | YAML 변경 / Agent 변경 |
| inventory_agent | 유일하게 미구현 | 구현 / 제거 |
| executor 네이밍 | `ml_agent.*` 패턴 통일 여부 | 현재 유지 / 통일 |
