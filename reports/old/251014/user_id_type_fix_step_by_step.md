# user_id 타입 변경 가이드 (단계별)

**Date**: 2025-10-14
**소요 시간**: 약 5분
**난이도**: ⭐ (매우 쉬움)

---

## 🎯 목표

**sessions 테이블의 user_id 타입을 String에서 Integer로 변경**

---

## ✅ Step 1: 첫 번째 파일 수정 (1분)

### 파일 위치
```
backend/app/models/session.py
```

### 수정할 줄
**Line 26**

### 변경 전 (현재)
```python
user_id = Column(String(100), nullable=True)
```

### 변경 후
```python
user_id = Column(Integer, nullable=True, index=True)
```

### 방법

#### 옵션 A: VS Code에서 직접 수정
1. VS Code에서 `backend/app/models/session.py` 열기
2. Ctrl+G 누르고 "26" 입력 (Line 26으로 이동)
3. Line 26의 내용을 위의 "변경 후" 코드로 교체
4. Ctrl+S로 저장

#### 옵션 B: 파일 탐색기에서 수정
1. `C:\kdy\Projects\holmesnyangz\beta_v001\backend\app\models\session.py` 파일 열기
2. Line 26 찾기
3. 수정 후 저장

---

## ✅ Step 2: 두 번째 파일 수정 (1분)

### 파일 위치
```
backend/migrations/create_sessions_table.sql
```

### 수정할 줄
**Line 8**

### 변경 전 (현재)
```sql
user_id VARCHAR(100),
```

### 변경 후
```sql
user_id INTEGER,
```

### 방법

1. VS Code에서 `backend/migrations/create_sessions_table.sql` 열기
2. Ctrl+G 누르고 "8" 입력 (Line 8으로 이동)
3. `VARCHAR(100)`을 `INTEGER`로 변경
4. Ctrl+S로 저장

---

## ✅ Step 3: PostgreSQL 테이블 재생성 (2분)

### 3-1. CMD 또는 PowerShell 열기

Windows 키 누르고 "cmd" 입력 후 Enter

### 3-2. 기존 테이블 삭제

```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "DROP TABLE IF EXISTS sessions;"
```

**예상 출력**:
```
DROP TABLE
```

### 3-3. 새 테이블 생성

```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -f backend/migrations/create_sessions_table.sql
```

**예상 출력**:
```
CREATE TABLE
CREATE INDEX
CREATE INDEX
```

---

## ✅ Step 4: 변경 확인 (1분)

### 4-1. 테이블 구조 확인

```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "\d sessions"
```

**예상 출력** (주목할 부분):
```
Column    | Type                     | Nullable
----------+--------------------------+----------
session_id| character varying(100)   | not null
user_id   | integer                  |          ← ✅ 여기가 integer면 성공!
metadata  | text                     |
...
```

### 4-2. SessionManager 테스트

```bash
cd backend
python test_session_migration.py
```

**예상 출력**:
```
[3/6] 세션 생성: ✅ PASS (user_id=123, type=<class 'int'>)  ← 타입 확인!
...
결과: 6/6 테스트 통과
🎉 모든 테스트 통과!
```

---

## 🔍 문제 해결

### 문제 1: "psql 명령을 찾을 수 없습니다"

**원인**: PostgreSQL이 PATH에 없음

**해결책**:
```bash
# 전체 경로로 실행
"C:\Program Files\PostgreSQL\17\bin\psql" "postgresql://postgres:root1234@localhost:5432/real_estate" -c "DROP TABLE IF EXISTS sessions;"
```

---

### 문제 2: "password authentication failed"

**원인**: 비밀번호가 틀림

**해결책**:
1. `backend/.env` 파일 열기
2. `DATABASE_URL` 확인
3. 올바른 비밀번호로 명령 다시 실행

---

### 문제 3: "relation already exists"

**원인**: 이미 테이블이 있음

**해결책**:
```bash
# 먼저 DROP 실행
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "DROP TABLE sessions;"

# 그 다음 CREATE 실행
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -f backend/migrations/create_sessions_table.sql
```

---

## 📋 전체 명령어 복사-붙여넣기용

**한 번에 실행** (CMD 또는 PowerShell에서):

```bash
# 1. 기존 테이블 삭제
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "DROP TABLE IF EXISTS sessions;"

# 2. 새 테이블 생성
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -f backend/migrations/create_sessions_table.sql

# 3. 확인
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "\d sessions"

# 4. 테스트
cd backend
python test_session_migration.py
```

---

## ✅ 완료 체크리스트

수정 완료 후 체크해주세요:

- [ ] `backend/app/models/session.py` Line 26 수정 완료
  ```python
  user_id = Column(Integer, nullable=True, index=True)
  ```

- [ ] `backend/migrations/create_sessions_table.sql` Line 8 수정 완료
  ```sql
  user_id INTEGER,
  ```

- [ ] PostgreSQL에서 sessions 테이블 삭제 완료
  ```
  DROP TABLE
  ```

- [ ] PostgreSQL에서 sessions 테이블 재생성 완료
  ```
  CREATE TABLE
  CREATE INDEX
  CREATE INDEX
  ```

- [ ] `\d sessions` 출력에서 user_id가 integer인지 확인
  ```
  user_id | integer |
  ```

- [ ] `python test_session_migration.py` 테스트 통과
  ```
  6/6 테스트 통과
  ```

---

## 🎉 성공 확인

테스트가 통과하면 다음과 같이 출력됩니다:

```
======================================================================
SessionManager PostgreSQL 마이그레이션 테스트
======================================================================
[1/6] PostgreSQL 연결: ✅ PASS
[2/6] sessions 테이블 확인: ✅ PASS
[3/6] 세션 생성: ✅ PASS (user_id=123, type=<class 'int'>)
[4/6] 세션 검증: ✅ PASS
[5/6] 세션 조회: ✅ PASS
[6/6] 활성 세션 수 조회: ✅ PASS

결과: 6/6 테스트 통과
🎉 모든 테스트 통과!
```

---

## 다음 단계

user_id 타입 변경이 완료되면:

✅ **Task 1 완료**: sessions.user_id 타입 수정

**다음 Task**: Task 2 - Long-term Memory 모델 생성
- 파일: `backend/app/models/memory.py` (신규 생성)
- 소요 시간: 약 2시간
- 난이도: ⭐⭐

---

**작업 시작하시겠습니까? 파일 수정 중 궁금한 점이 있으면 언제든 물어보세요!**

---

**Document End**
