# uv로 Backend 실행하기
작성일: 2025-10-30

## 프로젝트 구조

```
C:\kdy\Projects\holmesnyangz\beta_v001\
├── backend/                    ← Python 백엔드
│   └── app/
│       └── main.py            ← FastAPI 앱
├── frontend/                   ← React 프론트엔드
├── pyproject.toml             ← uv 설정 (루트)
├── .python-version            ← Python 3.12.7
├── .venv/                     ← uv 가상환경 (루트)
└── venv/                      ← 기존 venv (삭제 예정)
```

---

## uv 폴더 구조 전략

### ✅ Option 1: 모노레포 방식 (권장)

**현재 상태 그대로 사용**

```
루트/
├── pyproject.toml      ← 하나의 설정 파일 (모든 의존성)
├── .venv/             ← 하나의 가상환경
├── backend/           ← Python 코드
└── frontend/          ← React 코드
```

**장점**:
- ✅ 관리 간단 (하나의 pyproject.toml, 하나의 .venv)
- ✅ 의존성 공유 (backend, scripts, tools 모두 사용)
- ✅ 협업 쉬움 (하나의 uv.lock)
- ✅ 빌드/배포 간단

**단점**:
- ❌ 없음 (현재 프로젝트 구조에 최적)

### ❌ Option 2: 마이크로서비스 방식 (불필요)

**backend 폴더에도 별도 pyproject.toml**

```
루트/
├── pyproject.toml      ← 전체 프로젝트
├── .venv/
├── backend/
│   ├── pyproject.toml  ← backend 전용
│   └── .venv/         ← backend 전용
└── frontend/
```

**장점**:
- ✅ backend만 독립 배포 가능

**단점**:
- ❌ 복잡함 (2개 pyproject.toml, 2개 .venv 관리)
- ❌ 의존성 중복
- ❌ 협업 복잡 (어느 파일 사용?)
- ❌ 현재 프로젝트에 불필요

**결론**: **Option 1 (모노레포) 사용! 현재 상태 유지**

---

## 실행 방법 변경

### 기존 (venv)

```bash
# 1. venv 활성화
C:\kdy\Projects\holmesnyangz\beta_v001\venv\Scripts\activate

# 2. backend로 이동
cd backend

# 3. 실행
uvicorn app.main:app --reload
```

### 새로운 (uv) - 방법 1: 활성화 후 실행

```bash
# 1. 루트로 이동
cd C:\kdy\Projects\holmesnyangz\beta_v001

# 2. uv 가상환경 활성화
.venv\Scripts\activate

# 3. backend로 이동
cd backend

# 4. 실행
uvicorn app.main:app --reload
```

### 새로운 (uv) - 방법 2: uv run (권장) ⭐

```bash
# 1. 루트로 이동
cd C:\kdy\Projects\holmesnyangz\beta_v001

# 2. 바로 실행 (활성화 불필요!)
uv run uvicorn backend.app.main:app --reload
```

**장점**:
- ✅ 활성화 불필요
- ✅ 항상 올바른 가상환경 사용
- ✅ 짧고 간단

### 새로운 (uv) - 방법 3: backend에서 직접 실행

```bash
# 1. backend로 이동
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend

# 2. 상위 .venv 사용하여 실행
..\\.venv\Scripts\activate
uvicorn app.main:app --reload
```

---

## 추천 워크플로우

### 개발 시작

```bash
# 터미널 1: Backend 서버
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv run uvicorn backend.app.main:app --reload

# 터미널 2: Frontend 개발 서버
cd C:\kdy\Projects\holmesnyangz\beta_v001\frontend
npm run dev
```

### 스크립트 실행

```bash
# 예: DB 초기화
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv run python backend/scripts/init_db.py

# 예: 데이터 임포트
uv run python backend/scripts/import_apt_ofst.py
```

### 테스트 실행

```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv run pytest backend/tests/
```

---

## 실행 명령어 비교

| 작업 | venv (기존) | uv (새로운) |
|------|------------|------------|
| **활성화** | `venv\Scripts\activate` | `.venv\Scripts\activate` |
| **Backend 실행** | `cd backend && uvicorn app.main:app --reload` | `uv run uvicorn backend.app.main:app --reload` |
| **스크립트 실행** | `python backend/scripts/init_db.py` | `uv run python backend/scripts/init_db.py` |
| **테스트** | `pytest backend/tests/` | `uv run pytest backend/tests/` |
| **패키지 설치** | `pip install requests` | `uv add requests` |

---

## pyproject.toml에 실행 스크립트 추가 (선택)

### pyproject.toml에 추가

```toml
[project.scripts]
dev = "uvicorn backend.app.main:app --reload"
serve = "uvicorn backend.app.main:app"
init-db = "python backend/scripts/init_db.py"
test = "pytest backend/tests/"
```

### 사용 방법

```bash
# 개발 서버
uv run dev

# 프로덕션 서버
uv run serve

# DB 초기화
uv run init-db

# 테스트
uv run test
```

**장점**:
- ✅ 명령어 짧아짐
- ✅ 팀원들에게 표준화된 명령어 제공
- ✅ CI/CD에서 사용하기 좋음

---

## VSCode 설정 (선택)

### .vscode/settings.json

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.terminal.activateEnvironment": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "backend/tests"
  ]
}
```

### .vscode/launch.json (디버깅)

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "cwd": "${workspaceFolder}",
      "python": "${workspaceFolder}/.venv/Scripts/python.exe"
    }
  ]
}
```

---

## 환경 변수 (.env)

### 위치 확인

```
루트/
├── .env              ← 루트에 두는 게 일반적
├── backend/
│   └── .env         ← 또는 backend 폴더
└── .venv/
```

### 실행 시 환경변수 로드

```bash
# 루트 .env 사용
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv run uvicorn backend.app.main:app --reload

# backend/.env 사용
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend
uv run uvicorn app.main:app --reload
```

---

## 마이그레이션 체크리스트

### Step 1: uv 환경 구축
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv sync
```

### Step 2: 테스트 실행
```bash
# 방법 1: 활성화 후
.venv\Scripts\activate
cd backend
uvicorn app.main:app --reload

# 방법 2: uv run (권장)
uv run uvicorn backend.app.main:app --reload
```

### Step 3: 정상 작동 확인
- [ ] Backend 실행됨 (http://localhost:8000)
- [ ] API 문서 접근 가능 (http://localhost:8000/docs)
- [ ] DB 연결 정상
- [ ] WebSocket 연결 정상

### Step 4: 기존 venv 제거
```bash
# 정상 작동 확인 후
rmdir /s /q venv
```

---

## 트러블슈팅

### 문제 1: 모듈 못 찾음 (ModuleNotFoundError)

**증상**:
```
ModuleNotFoundError: No module named 'app'
```

**원인**: backend 폴더에서 실행 시 경로 문제

**해결**:
```bash
# 잘못된 방법
cd backend
uv run uvicorn app.main:app --reload  # ❌

# 올바른 방법 1 (루트에서)
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv run uvicorn backend.app.main:app --reload  # ✅

# 올바른 방법 2 (backend에서)
cd backend
uv run uvicorn app.main:app --reload  # ✅ (PYTHONPATH 자동 설정)
```

### 문제 2: 환경변수 못 읽음

**해결**:
```bash
# .env 파일 위치 확인
# 루트에 있으면 루트에서 실행
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv run uvicorn backend.app.main:app --reload
```

### 문제 3: uv run이 느림

**원인**: 매번 의존성 확인

**해결**: 활성화 후 사용
```bash
.venv\Scripts\activate
cd backend
uvicorn app.main:app --reload
```

---

## 협업자를 위한 README 추가

### README.md에 추가할 내용

```markdown
## Development Setup

### Prerequisites
- Python 3.12+
- uv (https://github.com/astral-sh/uv)
- Node.js 18+ (for frontend)

### Quick Start

1. Clone the repository
\`\`\`bash
git clone <repo-url>
cd beta_v001
\`\`\`

2. Install dependencies
\`\`\`bash
uv sync
\`\`\`

3. Setup environment variables
\`\`\`bash
cp .env.example .env
# Edit .env with your settings
\`\`\`

4. Initialize database
\`\`\`bash
uv run python backend/scripts/init_db.py
\`\`\`

5. Run backend server
\`\`\`bash
uv run uvicorn backend.app.main:app --reload
# Server: http://localhost:8000
# API Docs: http://localhost:8000/docs
\`\`\`

6. Run frontend (separate terminal)
\`\`\`bash
cd frontend
npm install
npm run dev
# Frontend: http://localhost:5173
\`\`\`

### Common Commands

\`\`\`bash
# Add a dependency
uv add <package-name>

# Run tests
uv run pytest backend/tests/

# Update dependencies
git pull
uv sync
\`\`\`
```

---

## 요약

### uv 폴더 구조
```
✅ 모노레포 방식 (현재 상태 유지)
- 루트에 pyproject.toml 하나
- 루트에 .venv 하나
- backend는 코드만
```

### 실행 방법
```bash
# 권장 (루트에서)
cd C:\kdy\Projects\holmesnyangz\beta_v001
uv run uvicorn backend.app.main:app --reload

# 또는 (backend에서)
cd backend
uv run uvicorn app.main:app --reload
```

### 핵심
- ✅ **별도 backend pyproject.toml 불필요**
- ✅ **루트 .venv 하나로 충분**
- ✅ **uv run으로 간단하게 실행**
- ✅ **현재 구조가 최적**

**마이그레이션 준비 완료! 바로 실행하세요** 🚀
