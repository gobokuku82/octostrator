# Backend Scripts

LangGraph 체크포인트 데이터베이스 설정 및 관리 스크립트.

## 사전 요구사항

- Python 3.11+
- PostgreSQL 15+ (실행 중이어야 함)
- 필수 패키지: `psycopg`, `langgraph-checkpoint-postgres`

```bash
pip install psycopg[binary] langgraph-checkpoint-postgres
```

---

## setup_checkpointer.py

PostgreSQL에 `dream_agent` 데이터베이스를 생성하고 LangGraph AsyncPostgresSaver에 필요한 테이블을 셋업합니다.

### 생성되는 테이블

| 테이블명 | 설명 |
|----------|------|
| `checkpoint_migrations` | 마이그레이션 버전 관리 |
| `checkpoints` | 체크포인트 메타데이터 |
| `checkpoint_blobs` | 체크포인트 데이터 (직렬화된 상태) |
| `checkpoint_writes` | 체크포인트 쓰기 기록 |

---

## 실행 방법

### Windows (PowerShell / CMD)

```powershell
# 프로젝트 루트에서 실행
cd C:\kdy\Projects\mind_dream\beta_v001
python -m backend.scripts.setup_checkpointer
```

### Windows (Git Bash)

```bash
# 프로젝트 루트에서 실행
cd /c/kdy/Projects/mind_dream/beta_v001
python -m backend.scripts.setup_checkpointer
```

### macOS / Linux

```bash
# 프로젝트 루트에서 실행
cd ~/Projects/mind_dream/beta_v001
python -m backend.scripts.setup_checkpointer
```

---

## 설정 변경

스크립트 내 기본 설정을 변경하려면 `setup_checkpointer.py`의 상단 설정 부분을 수정하세요:

```python
# ========================================
# 설정
# ========================================
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "root1234"  # 본인 비밀번호로 변경
DATABASE_NAME = "dream_agent"
```

---

## 출력 예시

```
============================================================
LangGraph Checkpoint Database Setup
============================================================
[1/3] PostgreSQL에 연결 중... (localhost:5432)
      데이터베이스 'dream_agent' 생성 완료!

[2/3] 체크포인트 테이블 생성 중...
      연결: dream_agent@localhost
      체크포인트 테이블 생성 완료!
      - checkpoint_migrations
      - checkpoints
      - checkpoint_blobs
      - checkpoint_writes

[검증] 테이블 확인 중...
      생성된 테이블:
        - checkpoint_blobs
        - checkpoint_migrations
        - checkpoint_writes
        - checkpoints

[3/3] .env 파일에 다음 설정을 추가하세요:
============================================================
# Checkpoint Database (LangGraph AsyncPostgresSaver)
CHECKPOINT_DB_URI=postgresql://postgres:root1234@localhost:5432/dream_agent
============================================================

✓ 셋업 완료!
```

---

## 문제 해결

### PostgreSQL 연결 실패

```
오류: PostgreSQL 연결 실패
```

**해결방법:**
1. PostgreSQL 서비스가 실행 중인지 확인
   - Windows: `services.msc`에서 PostgreSQL 서비스 확인
   - macOS: `brew services list | grep postgresql`
   - Linux: `sudo systemctl status postgresql`

2. 포트 확인 (기본: 5432)
   ```bash
   # 포트 사용 확인
   # Windows
   netstat -an | findstr 5432

   # macOS/Linux
   lsof -i :5432
   ```

### 권한 오류

```
오류: permission denied to create database
```

**해결방법:**
- PostgreSQL 사용자에게 CREATE DATABASE 권한이 있는지 확인
- 또는 superuser 계정(postgres)으로 실행

### Windows 이벤트 루프 오류

```
Psycopg cannot use the 'ProactorEventLoop'
```

**해결방법:**
- 스크립트에 이미 `WindowsSelectorEventLoopPolicy` 설정이 포함되어 있음
- 문제 지속시 Python 버전 확인 (3.11+ 권장)

---

## 참고 자료

- [langgraph-checkpoint-postgres (PyPI)](https://pypi.org/project/langgraph-checkpoint-postgres/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Psycopg 3 Documentation](https://www.psycopg.org/psycopg3/docs/)
