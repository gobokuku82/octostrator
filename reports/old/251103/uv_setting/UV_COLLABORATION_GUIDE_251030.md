# uv 협업 가이드
작성일: 2025-10-30

## Git으로 공유할 파일 vs 무시할 파일

### ✅ Git에 커밋해야 할 파일 (협업자와 공유)

```
C:\kdy\Projects\holmesnyangz\beta_v001\
├── pyproject.toml       ✅ 커밋 (의존성 정의)
├── uv.lock             ✅ 커밋 (버전 잠금)
├── .python-version     ✅ 커밋 (Python 버전)
├── requirements.txt     ⚠️  선택 (백업용, 점진적 제거 가능)
└── README.md           ✅ 커밋 (uv 사용법 추가)
```

### ❌ Git에서 무시해야 할 파일 (.gitignore)

```
.venv/                  ❌ 무시 (가상환경)
venv/                   ❌ 무시 (기존 가상환경)
__pycache__/            ❌ 무시
*.pyc                   ❌ 무시
.env                    ❌ 무시 (환경변수)
```

---

## 협업 워크플로우

### 📤 당신 (uv 설정 후 공유)

#### Step 1: uv 환경 구축
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001

# 1. uv 환경 생성
uv sync

# 2. 테스트
.venv\Scripts\activate
python -c "import langchain, langgraph, fastapi"

# 3. 정상 작동 확인
uvicorn backend.app.main:app --reload
```

#### Step 2: .gitignore 업데이트
```bash
# .gitignore에 uv 관련 추가 (아래 섹션 참고)
```

#### Step 3: Git 커밋
```bash
# 공유할 파일만 커밋
git add pyproject.toml
git add uv.lock
git add .python-version
git add .gitignore

# 선택: requirements.txt도 백업용으로 유지
git add requirements.txt

git commit -m "Migrate to uv package manager

- Add pyproject.toml with 185 dependencies
- Add uv.lock for version pinning
- Set Python version to 3.12.7
- Update .gitignore for uv

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

### 📥 협업자 (파일 받은 후)

#### Step 1: 파일 받기
```bash
git pull
```

**받게 되는 파일**:
- `pyproject.toml` (의존성 정의)
- `uv.lock` (정확한 버전)
- `.python-version` (Python 3.12.7)

#### Step 2: uv 설치 (없으면)
```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# 설치 확인
uv --version
```

#### Step 3: 환경 구축
```bash
cd <프로젝트-경로>

# uv.lock 기반으로 정확히 같은 환경 설치
uv sync

# 완료! 동일한 환경 구축됨
```

#### Step 4: 활성화 및 작업
```bash
# 가상환경 활성화
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 작업 시작
python backend/app/main.py
```

---

## .gitignore 업데이트 필요

### 현재 .gitignore 상태
```gitignore
# Python
venv/         ← 있음 ✓
env/          ← 있음 ✓
ENV/          ← 있음 ✓
```

### 추가해야 할 내용
```gitignore
# uv
.venv/                    ← 추가 필요
.python-version.bak       ← 추가 권장
uv.lock.bak              ← 추가 권장

# 기존 venv (마이그레이션 후 삭제 예정)
venv/                     ← 이미 있음 ✓
```

---

## 파일별 역할 정리

### 1. pyproject.toml
- **역할**: 프로젝트 의존성 정의
- **Git**: ✅ 커밋 필수
- **이유**: 협업자가 어떤 패키지가 필요한지 알아야 함
- **변경 시**: 의존성 추가/제거할 때마다 커밋

### 2. uv.lock
- **역할**: 정확한 버전과 해시 잠금
- **Git**: ✅ 커밋 필수
- **이유**: 모든 팀원이 정확히 같은 버전 사용
- **변경 시**: `uv sync` 실행 시 자동 업데이트, 커밋

### 3. .python-version
- **역할**: Python 버전 명시
- **Git**: ✅ 커밋 권장
- **이유**: 모든 팀원이 같은 Python 버전 사용
- **내용**: `3.12.7`

### 4. .venv/
- **역할**: 가상환경 (패키지 실제 설치 위치)
- **Git**: ❌ 무시 필수
- **이유**:
  - 용량 큰 (수백 MB ~ GB)
  - 각자 `uv sync`로 생성
  - OS/환경마다 다를 수 있음

### 5. requirements.txt (선택)
- **역할**: 백업/레거시 호환
- **Git**: ⚠️ 선택
- **점진적 제거**: uv 전환 후 불필요
- **유지 이유**:
  - CI/CD가 아직 requirements.txt 사용
  - 일부 도구 호환성
  - 백업용

---

## 협업 시나리오

### Scenario 1: 의존성 추가

#### 당신 (패키지 추가)
```bash
# 새 패키지 추가
uv add requests

# 자동으로:
# - pyproject.toml 업데이트
# - uv.lock 업데이트
# - .venv에 설치

# Git 커밋
git add pyproject.toml uv.lock
git commit -m "Add requests package"
git push
```

#### 협업자 (업데이트 받기)
```bash
git pull

# 의존성 동기화 (새 패키지 자동 설치)
uv sync

# 완료! requests 사용 가능
```

### Scenario 2: 협업자가 의존성 추가

#### 협업자
```bash
uv add pandas
git add pyproject.toml uv.lock
git commit -m "Add pandas for data analysis"
git push
```

#### 당신 (업데이트 받기)
```bash
git pull
uv sync  # pandas 자동 설치
```

### Scenario 3: Python 버전 업그레이드

#### 당신
```bash
# .python-version 수정
echo "3.12.8" > .python-version

# 재구축
uv sync

# 커밋
git add .python-version uv.lock
git commit -m "Upgrade to Python 3.12.8"
git push
```

#### 협업자
```bash
git pull

# Python 3.12.8 설치 (수동)
# 설치 후:
uv sync
```

---

## 협업 체크리스트

### 초기 설정 (한 번만)

- [ ] pyproject.toml 생성
- [ ] .python-version 생성
- [ ] .gitignore 업데이트 (.venv/ 추가)
- [ ] README.md 업데이트 (uv 사용법)
- [ ] 파일 커밋 및 푸시
- [ ] 팀원들에게 공지

### 일상 작업

**패키지 추가/제거 시**:
- [ ] `uv add <package>` 또는 `uv remove <package>`
- [ ] `git add pyproject.toml uv.lock`
- [ ] `git commit` 및 `git push`

**다른 사람 변경사항 받을 때**:
- [ ] `git pull`
- [ ] `uv sync` (자동으로 의존성 업데이트)

**새 브랜치 작업 시**:
- [ ] `git checkout <branch>`
- [ ] `uv sync` (브랜치별 의존성 동기화)

---

## 문제 해결

### 문제 1: 협업자가 uv.lock 충돌

**상황**: 두 사람이 동시에 의존성 추가
```
<<<<<<< HEAD
package-a
=======
package-b
>>>>>>> feature-branch
```

**해결**:
```bash
# 1. 충돌 해결 (두 패키지 모두 유지)
# 2. 재생성
uv lock
uv sync

# 3. 커밋
git add uv.lock
git commit -m "Resolve uv.lock conflict"
```

### 문제 2: 버전 불일치

**증상**: 협업자 환경에서 에러 발생

**해결**:
```bash
# 1. uv.lock 삭제 후 재생성
rm uv.lock
uv lock
uv sync

# 2. 테스트 후 커밋
git add uv.lock
git commit -m "Regenerate uv.lock"
git push
```

### 문제 3: .venv가 Git에 올라감

**해결**:
```bash
# 1. .gitignore 확인 및 추가
echo ".venv/" >> .gitignore

# 2. Git에서 제거 (실제 파일은 유지)
git rm -r --cached .venv

# 3. 커밋
git add .gitignore
git commit -m "Add .venv to .gitignore"
git push
```

---

## 비교: pip vs uv 협업

### pip 시대
```bash
# 공유 파일
requirements.txt  ← 커밋

# 협업자
git pull
pip install -r requirements.txt  # 버전 다를 수 있음

# 문제점
- 버전 불일치 가능
- 의존성 해결 느림
- 환경 재현 어려움
```

### uv 시대
```bash
# 공유 파일
pyproject.toml    ← 커밋
uv.lock          ← 커밋 (정확한 버전)

# 협업자
git pull
uv sync          # 정확히 같은 환경

# 장점
- ✅ 100% 동일한 환경 보장
- ✅ 빠른 설치 (10-100배)
- ✅ 자동 의존성 해결
- ✅ 버전 충돌 사전 방지
```

---

## 요약

### 공유할 파일 (Git 커밋)
```
✅ pyproject.toml    (의존성 정의)
✅ uv.lock          (버전 잠금)
✅ .python-version  (Python 버전)
✅ .gitignore       (업데이트)
⚠️  requirements.txt (선택, 백업용)
```

### 무시할 파일 (.gitignore)
```
❌ .venv/           (가상환경)
❌ venv/            (기존 가상환경)
❌ __pycache__/
❌ *.pyc
```

### 협업자가 할 일
```bash
# 1단계: 파일 받기
git pull

# 2단계: 환경 구축 (자동)
uv sync

# 완료! 작업 시작
```

**핵심**: pyproject.toml + uv.lock만 공유하면, 협업자는 `uv sync` 한 번으로 동일한 환경 구축! 🎉
