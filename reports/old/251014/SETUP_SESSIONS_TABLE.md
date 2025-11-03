# Sessions 테이블 생성 가이드 (초보자용)

**대상**: 새로 프로젝트에 참여하는 개발자
**소요 시간**: 1분
**목적**: SessionManager용 sessions 테이블 생성

---

## 📋 사전 확인

### 필요한 정보
1. PostgreSQL 비밀번호 (예: `root1234`)
2. 데이터베이스 이름 (예: `real_estate`)

### 확인 방법
```bash
# .env 파일에서 확인
type backend\.env
```

**예시**:
```env
DATABASE_URL=postgresql+psycopg://postgres:root1234@localhost:5432/real_estate
                                          ↑          ↑                    ↑
                                      비밀번호    포트(5432)         DB 이름
```

---

## 🚀 실행 단계

### 1. CMD 열기
- Windows 키 누르기
- `cmd` 입력
- Enter

### 2. 프로젝트 폴더로 이동
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend
```

**또는 자신의 프로젝트 경로로**:
```bash
cd [프로젝트_경로]\backend
```

### 3. sessions 테이블 생성 명령어 실행

**형식**:
```bash
psql "postgresql://postgres:[your_password]@localhost:5432/[database_name]" -f migrations\create_sessions_table.sql
```

**실제 예시** (비밀번호: `root1234`, DB: `real_estate`):
```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -f migrations\create_sessions_table.sql
```

**성공 시 출력**:
```
CREATE TABLE
CREATE INDEX
CREATE INDEX
```

### 4. 확인 (선택 사항)

```bash
psql "postgresql://postgres:[your_password]@localhost:5432/[database_name]" -c "\dt sessions"
```

**예시**:
```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "\dt sessions"
```

**성공 시 출력**:
```
          List of relations
 Schema |   Name   | Type  |  Owner
--------+----------+-------+----------
 public | sessions | table | postgres
```

---

## 🎯 요약 (복사해서 사용)

### 비밀번호가 `root1234`, DB가 `real_estate`인 경우:

```bash
# 1. CMD 열기 (Windows 키 → cmd)

# 2. 프로젝트 폴더로 이동
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend

# 3. sessions 테이블 생성
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -f migrations\create_sessions_table.sql

# 4. 확인
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "\dt sessions"
```

---

## ❓ 문제 해결

### 오류 1: "psql은(는) 내부 또는 외부 명령이 아닙니다"

**원인**: PostgreSQL이 PATH에 없음

**해결**:
```bash
# 전체 경로로 실행
"C:\Program Files\PostgreSQL\17\bin\psql" "postgresql://postgres:root1234@localhost:5432/real_estate" -f migrations\create_sessions_table.sql
```

### 오류 2: "connection refused"

**원인**: PostgreSQL 서버가 실행되지 않음

**해결**:
1. Windows 키 + R
2. `services.msc` 입력
3. `postgresql-x64-17` 찾기
4. 우클릭 → 시작

### 오류 3: "password authentication failed"

**원인**: 비밀번호가 틀림

**해결**: `.env` 파일에서 정확한 비밀번호 확인

### 오류 4: "relation already exists"

**원인**: 이미 테이블이 생성되어 있음

**해결**: 문제 없습니다! 이미 완료된 상태입니다.

---

## ✅ 완료 후

sessions 테이블 생성 후 서버를 시작하면:
- ✅ sessions 테이블: 수동 생성 완료
- ✅ checkpoints 테이블: 자동 생성 (서버 시작 시)
- ✅ checkpoint_blobs 테이블: 자동 생성 (서버 시작 시)
- ✅ checkpoint_writes 테이블: 자동 생성 (서버 시작 시)

**총 4개 시스템 테이블 준비 완료!**

---

**작성일**: 2025-10-14
**작성자**: Claude Code
