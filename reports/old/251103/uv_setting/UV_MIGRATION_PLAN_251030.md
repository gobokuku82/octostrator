# UV 마이그레이션 계획서
작성일: 2025-10-30

## 1. 현재 상황

### 현재 환경
- **Python 버전**: 3.12.7 (venv)
- **패키지 관리**: venv + pip
- **uv 설치 여부**: ✅ 이미 설치됨 (v0.9.2)
- **의존성 파일**: requirements.txt (185개 패키지)
- **venv 경로**: C:\kdy\Projects\holmesnyangz\beta_v001\venv

### 협업 현황
- **개인**: venv 사용 중
- **협업자들**: uv 사용 중
- **결정**: uv로 통일 (다수결)

---

## 2. 협업자 저장소에서 가져와야 할 파일

### 필수 파일
다음 파일들이 협업자의 git 저장소에 있는지 확인하고 복사해야 합니다:

1. **`pyproject.toml`** (필수)
   - 프로젝트 메타데이터 및 의존성 정의
   - uv의 핵심 설정 파일
   - 위치: 프로젝트 루트 (C:\kdy\Projects\holmesnyangz\beta_v001\)

2. **`uv.lock`** (권장)
   - 정확한 의존성 버전 잠금 파일
   - 협업 시 동일한 환경 보장
   - 위치: 프로젝트 루트

3. **`.python-version`** (✅ 생성 완료)
   - 프로젝트의 Python 버전 명시
   - 위치: 프로젝트 루트
   - 내용: `3.12.7`
   - 상태: 이미 생성됨

### 확인 방법
협업자에게 다음 파일들을 요청하세요:
```bash
# 협업자 저장소에서
git ls-files | grep -E "(pyproject.toml|uv.lock|.python-version)"
```

---

## 3. venv → uv 마이그레이션 단계

### Phase 1: 준비 단계

#### 1.1 백업 생성
```bash
# 현재 venv 환경 백업
pip freeze > requirements_backup_$(date +%Y%m%d).txt

# 또는 Windows에서
pip freeze > requirements_backup_251030.txt
```

#### 1.2 협업자 파일 복사
협업자로부터 받은 파일을 프로젝트 루트에 복사:
- `pyproject.toml` → `C:\kdy\Projects\holmesnyangz\beta_v001\`
- `uv.lock` → `C:\kdy\Projects\holmesnyangz\beta_v001\`
- `.python-version` → ✅ 이미 생성됨 (3.12.7)

### Phase 2: uv 설정

#### 2.1 기존 venv 비활성화
```bash
# venv 비활성화 (현재 활성화되어 있다면)
deactivate
```

#### 2.2 uv로 가상환경 생성
```bash
# 프로젝트 루트로 이동
cd C:\kdy\Projects\holmesnyangz\beta_v001

# uv.lock이 있는 경우 (협업자에게서 받음)
uv sync

# 또는 pyproject.toml만 있는 경우
uv venv
uv pip install -e .
```

#### 2.3 의존성 설치
```bash
# pyproject.toml 기반으로 설치
uv sync

# 또는 기존 requirements.txt 사용
uv pip install -r requirements.txt
```

### Phase 3: 검증

#### 3.1 설치 확인
```bash
# uv 환경 활성화
.venv\Scripts\activate  # Windows

# 설치된 패키지 확인
uv pip list

# 주요 패키지 테스트
python -c "import langchain, langgraph, fastapi, anthropic"
```

#### 3.2 프로젝트 실행 테스트
```bash
# Backend 테스트
cd backend
uvicorn app.main:app --reload

# Frontend 테스트 (별도 터미널)
cd frontend
npm run dev
```

### Phase 4: 정리

#### 4.1 기존 venv 제거
```bash
# 정상 작동 확인 후
rmdir /s /q venv  # Windows
```

#### 4.2 .gitignore 업데이트
```gitignore
# uv 관련 추가
.venv/
.python-version
uv.lock

# 기존 venv 제거 (이미 있을 수 있음)
venv/
```

---

## 4. pyproject.toml 없는 경우 (직접 생성)

만약 협업자에게 `pyproject.toml`이 없다면, 다음과 같이 생성할 수 있습니다:

```bash
# requirements.txt에서 pyproject.toml 생성
uv pip compile requirements.txt -o pyproject.toml
```

또는 수동으로 생성:

```toml
[project]
name = "holmesnyangz"
version = "0.1.0"
description = "Real Estate AI Chatbot"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "langchain>=0.3.27",
    "langgraph>=0.6.8",
    "anthropic>=0.69.0",
    # ... 나머지 의존성들
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## 5. 협업 워크플로우

### 일반 작업
```bash
# 의존성 추가
uv add <package-name>

# 개발 의존성 추가
uv add --dev <package-name>

# 의존성 업데이트
uv sync

# 의존성 제거
uv remove <package-name>
```

### Git 워크플로우
```bash
# 1. 변경사항 pull
git pull

# 2. 의존성 동기화 (uv.lock 변경 시)
uv sync

# 3. 작업 후 commit
git add pyproject.toml uv.lock
git commit -m "Update dependencies"
git push
```

---

## 6. 트러블슈팅

### 문제 1: uv sync 실패
```bash
# 캐시 초기화
uv cache clean

# 다시 시도
uv sync
```

### 문제 2: 패키지 버전 충돌
```bash
# uv.lock 재생성
rm uv.lock
uv lock
uv sync
```

### 문제 3: Python 버전 불일치
```bash
# .python-version 확인
cat .python-version

# 해당 버전 설치 필요
# Python 3.12.7 설치 후 다시 시도
```

---

## 7. uv의 장점

1. **속도**: pip보다 10-100배 빠른 의존성 해결
2. **일관성**: uv.lock으로 모든 환경에서 동일한 버전 보장
3. **단순성**: 하나의 도구로 venv + pip 역할 수행
4. **협업**: 팀원들과 정확히 같은 환경 공유

---

## 8. 체크리스트

### 마이그레이션 전
- [ ] 현재 환경 백업 (`pip freeze`)
- [ ] 협업자에게 `pyproject.toml`, `uv.lock` 요청
- [ ] uv 설치 확인 (`uv --version`)

### 마이그레이션 중
- [ ] 협업자 파일 복사 완료
- [ ] `uv sync` 성공
- [ ] 주요 패키지 import 테스트
- [ ] Backend 실행 테스트
- [ ] Frontend 실행 테스트

### 마이그레이션 후
- [ ] 기존 venv 폴더 제거
- [ ] .gitignore 업데이트
- [ ] 팀원들에게 완료 알림

---

## 9. 다음 단계

1. **즉시**: 협업자에게 `pyproject.toml`, `uv.lock` 파일 요청
2. **받은 후**: Phase 1-4 순서대로 진행
3. **완료 후**: 팀 워크플로우(섹션 5)에 따라 작업

---

## 참고 자료

- [uv 공식 문서](https://github.com/astral-sh/uv)
- [uv 마이그레이션 가이드](https://docs.astral.sh/uv/guides/migration/)
