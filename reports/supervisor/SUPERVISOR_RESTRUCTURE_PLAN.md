# Supervisor 구조 개선 계획

## 현재 상태
```
supervisor/
├── nodes/     (cognitive + response 혼재)
├── helpers/   (cognitive + execute 혼재)
├── prompts/   (하나의 파일에 모든 프롬프트)
└── graphs/    (main_graph 하나만)
```

## 목표 상태
```
supervisor/
├── layers/
│   ├── cognitive/  (Layer 1: 독립 패키지)
│   ├── execute/    (Layer 3: 독립 패키지)
│   └── response/   (응답 생성)
├── core/          (오케스트레이션)
├── shared/        (공유 리소스)
└── monitoring/    (디버깅/성능)
```

## 단계별 실행 계획

### Phase 1: 기본 구조 생성 (즉시)
```bash
# 1. 레이어 폴더 생성
mkdir -p supervisor/layers/cognitive
mkdir -p supervisor/layers/execute
mkdir -p supervisor/layers/response
mkdir -p supervisor/core
mkdir -p supervisor/shared
mkdir -p supervisor/monitoring

# 2. 테스트 폴더 생성
mkdir -p supervisor/layers/cognitive/tests
mkdir -p supervisor/layers/execute/tests
```

### Phase 2: 파일 재배치 (1시간)
```
이동 계획:
- nodes/cognitive_nodes.py → layers/cognitive/nodes.py
- helpers/cognitive_supervisor.py → layers/cognitive/supervisor.py
- helpers/execute_supervisor.py → layers/execute/supervisor.py
- nodes/response_nodes.py → layers/response/generators.py
- prompts/cognitive_prompts.py → 각 레이어 prompts.py로 분리
```

### Phase 3: 인터페이스 정의 (2시간)
```python
# shared/interfaces.py
class LayerInterface(ABC):
    @abstractmethod
    async def process(self, input_data: Dict) -> Dict:
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict) -> bool:
        pass
```

### Phase 4: 레이어별 Graph 생성 (3시간)
```python
# layers/cognitive/graph.py
def build_cognitive_graph():
    """Cognitive 레이어만의 독립 그래프"""
    pass

# layers/execute/graph.py
def build_execute_graph():
    """Execute 레이어만의 독립 그래프"""
    pass
```

### Phase 5: 통합 테스트 (2시간)
- 각 레이어 독립 실행 테스트
- 전체 파이프라인 테스트
- 성능 벤치마크

## 예상 효과

1. **개발 속도**: 30% 향상 (독립 개발 가능)
2. **디버깅 시간**: 50% 감소 (명확한 분리)
3. **테스트 커버리지**: 80% 이상 달성 가능
4. **팀 생산성**: 병렬 작업으로 2배 향상

## 위험 요소 및 대응

1. **위험**: 기존 코드 깨짐
   - **대응**: 임시 호환성 레이어 유지

2. **위험**: 레이어 간 통신 복잡도
   - **대응**: 명확한 인터페이스 정의

3. **위험**: 성능 저하
   - **대응**: 캐싱 레이어 추가

## 체크리스트

### 즉시 실행
- [ ] todo_manager 폴더 생성 완료
- [ ] TodoAgent 이동 완료
- [ ] supervisor/layers 구조 생성

### 오늘 내
- [ ] Cognitive 레이어 분리
- [ ] Execute 레이어 분리
- [ ] Response 레이어 분리

### 이번 주
- [ ] 인터페이스 정의 완료
- [ ] 레이어별 테스트 작성
- [ ] 통합 테스트 완료

## 결론

이 구조는:
- **확장성**: 새 레이어 쉽게 추가 ✅
- **디버깅**: 독립 테스트 가능 ✅
- **팀 협업**: 명확한 경계 ✅
- **성능**: 최적화 가능 ✅
- **독립 실행**: 레이어별 실행 ✅

모든 요구사항을 충족하는 최적 구조입니다.