# 채팅 시스템 구조 분석 및 수정 계획

**날짜**: 2025-10-16
**작성자**: Claude Code
**상태**: Phase 0 - 구조 파악 중 🔍

---

## 📋 목차

1. [사용자 요구사항](#1-사용자-요구사항)
2. [현재 구조 파악](#2-현재-구조-파악-읽기-전용)
3. [발견된 문제점](#3-발견된-문제점)
4. [수정 계획](#4-수정-계획)
5. [테스트 시나리오](#5-테스트-시나리오)

---

## 1. 사용자 요구사항

### 핵심 요구사항 (4가지)

1. ✅ **채팅 대화 기록 저장**
   - 사용자 메시지와 AI 응답을 DB에 저장

2. ✅ **F5 새로고침 시 대화 유지**
   - 브라우저 새로고침해도 현재 대화 내역 그대로 유지

3. ✅ **언제든 불러와서 이어서 대화**
   - 과거 대화 목록 조회 가능
   - 원하는 대화를 선택해서 이어서 채팅 가능

4. ✅ **접속 시 새로운 채팅창부터 시작**
   - 첫 접속 시 깨끗한 새 채팅으로 시작
   - 필요하면 과거 대화 불러오기

---

## 2. 현재 구조 파악 (읽기 전용)

### 2.1 Backend 구조

#### POST /api/v1/chat/start
**역할**: 새 세션 생성

**흐름**:
```
1. Frontend → POST /start 호출
2. PostgreSQLSessionManager.create_session()
   → 어디에 저장? (Redis? DB?)
3. chat_sessions 테이블에 INSERT (✅ 수정됨)
4. session_id 반환 (형식: "session-{uuid}")
```

**확인 필요**:
- [ ] PostgreSQLSessionManager는 어디에 세션 저장?
- [ ] chat_sessions 테이블 INSERT 정상 작동?
- [ ] 세션 만료 정책은?

#### GET /api/v1/chat/{session_id}
**역할**: 세션 정보 조회

**흐름**:
```
1. Frontend → GET /{session_id} 호출
2. session_mgr.get_session(session_id)
   → 어디서 조회? (Redis? DB?)
3. SessionInfo 반환
```

**현재 문제**:
- ❌ 404 에러 발생 (세션이 만료되었거나 없음)
- ❌ `postgres_session_manager`에서만 조회 → DB 테이블 조회 안 함

**확인 필요**:
- [ ] GET /{session_id}가 chat_sessions 테이블에서 조회하는가?
- [ ] 만료 시간은 얼마인가?

#### WebSocket /api/v1/chat/ws/{session_id}
**역할**: 실시간 메시지 송수신

**흐름**:
```
1. Frontend → WebSocket 연결
2. 메시지 수신: _process_query_async()
3. _save_message_to_db() → chat_messages 테이블 INSERT
4. Supervisor 처리
5. 응답 생성
6. _save_message_to_db() → chat_messages 테이블 INSERT
7. WebSocket으로 응답 전송
```

**확인 필요**:
- [ ] _save_message_to_db() 정상 작동?
- [ ] 호출 시점 정확한가?

#### GET /api/v1/chat/sessions/{session_id}/messages
**역할**: 세션의 메시지 목록 조회

**상태**: ✅ 이미 구현됨

**확인 필요**:
- [ ] 제대로 작동하는가?
- [ ] Frontend에서 호출하는가?

---

### 2.2 Frontend 구조

#### use-session.ts
**역할**: 세션 생성 및 관리

**흐름**:
```
1. useEffect 실행 (컴포넌트 마운트)
2. sessionStorage에서 기존 세션 확인
3. 있으면: GET /{session_id} 검증
4. 없으면: POST /start 호출하여 새 세션 생성
5. sessionStorage에 저장
```

**현재 문제**:
- ❌ React Strict Mode → useEffect 2번 실행
- ❌ 세션이 2개씩 생성됨
- ❌ GET /{session_id} 404 → 계속 새 세션 생성

**확인 필요**:
- [ ] React Strict Mode 비활성화 필요?
- [ ] useEffect dependency 정확한가?

#### chat-interface.tsx
**역할**: 채팅 UI 및 메시지 관리

**주요 기능**:
1. WebSocket 연결 관리
2. 메시지 송수신
3. DB에서 메시지 로드 (✅ 추가됨)
4. localStorage 저장/복원 (❌ DEPRECATED)

**현재 문제**:
- ❌ handleWSMessage ReferenceError (순서 문제)
- ❌ DB 메시지 로드 안 됨 (useEffect 실행 안 됨?)
- ❌ 무한 루프 발생 (세션 계속 생성)

**확인 필요**:
- [ ] handleWSMessage 위치 정확한가? (Line 112?)
- [ ] DB 로드 useEffect 실행되는가?
- [ ] localStorage 완전히 제거할 것인가?

#### chat_session_id vs session_id
**문제**: 2가지 ID가 혼재

- `session_id`: Backend 생성, sessionStorage 저장
- `chat_session_id`: Frontend 생성, localStorage 저장, **사용 안 됨!**

**확인 필요**:
- [ ] chat_session_id 완전히 제거할 것인가?

---

### 2.3 Database 구조

#### chat_sessions 테이블
```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL DEFAULT 1,
    title VARCHAR(200) NOT NULL DEFAULT '새 대화',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message TEXT,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB
);
```

**확인 필요**:
- [ ] 현재 몇 개 세션 저장되어 있는가?
- [ ] 중복 세션 있는가?

#### chat_messages 테이블
```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL
        REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL
        CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**확인 필요**:
- [ ] 메시지가 정상적으로 저장되는가?
- [ ] 세션별 메시지 개수는?

---

## 3. 발견된 문제점

### P0 (최우선) - 세션이 2개씩 생성됨

**증상**:
```
✅ New session created: session-8b15a80a-fc8d-40b3-91d6-9fd8fa6886c9
✅ New session created: session-3892c944-84ec-4834-8d96-5cfbf4ef78e2
```

**원인 추정**:
1. React Strict Mode → useEffect 2번 실행 (개발 모드)
2. use-session.ts의 initSession() 중복 호출
3. GET /{session_id} 404 에러 → 계속 새 세션 생성

**영향**:
- DB에 불필요한 세션 누적
- WebSocket 연결 혼란
- 무한 루프 발생 가능성

---

### P1 (필수) - GET /{session_id} 404 에러

**증상**:
```
GET http://localhost:8000/api/v1/chat/session-8e3ea97b-b778-4973-ad31-ca50af455898 404 (Not Found)
⚠️ Session expired or invalid, creating new session
```

**원인**:
- `session_mgr.get_session()`이 `postgres_session_manager`에서 조회
- 세션이 만료되었거나 Redis/메모리에만 있음
- `chat_sessions` 테이블에서 조회하지 않음

**영향**:
- 브라우저 새로고침할 때마다 새 세션 생성
- 대화 내역 유지 불가

---

### P2 (중요) - F5 새로고침 시 메시지 안 불러옴

**증상**:
```
[ChatInterface] No messages in DB, keeping welcome message
```

**원인 추정**:
1. DB 메시지 로드 useEffect가 실행 안 됨
2. sessionId가 계속 바뀌어서 이전 메시지 조회 불가
3. API 호출 실패 (404 또는 네트워크 에러)

**영향**:
- F5 누르면 대화 내역 사라짐
- 사용자 경험 저하

---

### P3 (개선) - handleWSMessage ReferenceError

**증상**:
```
ReferenceError: Cannot access 'handleWSMessage' before initialization
```

**원인**:
- handleWSMessage 정의 (Line 112)가 WebSocket useEffect (Line 267)보다 앞에 있어야 함
- 현재 순서가 잘못됨

**영향**:
- 페이지 로드 에러
- WebSocket 연결 실패

**해결 시도**:
- handleWSMessage를 useCallback으로 감쌈 (✅ 완료)
- WebSocket useEffect 위로 이동 (✅ 완료)

**확인 필요**:
- [ ] 여전히 에러 발생하는가?

---

## 4. 수정 계획

### Step 1: 현재 상태 완전 파악 (읽기 전용) ⏳

**목표**: 코드 수정 전에 현재 시스템 완전히 이해

**작업**:
1. Backend 코드 읽기
   - [ ] POST /start 흐름 확인
   - [ ] GET /{session_id} 흐름 확인
   - [ ] WebSocket handler 확인
   - [ ] _save_message_to_db() 확인

2. Frontend 코드 읽기
   - [ ] use-session.ts 흐름 확인
   - [ ] chat-interface.tsx useEffect 순서 확인
   - [ ] handleWSMessage 위치 확인

3. Database 조회
   ```sql
   -- 세션 목록
   SELECT session_id, title, created_at, updated_at
   FROM chat_sessions
   ORDER BY created_at DESC
   LIMIT 10;

   -- 메시지 목록
   SELECT session_id, role, substring(content, 1, 50), created_at
   FROM chat_messages
   ORDER BY created_at DESC
   LIMIT 10;

   -- 세션별 메시지 개수
   SELECT cs.session_id, cs.title, COUNT(cm.id) as msg_count
   FROM chat_sessions cs
   LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
   GROUP BY cs.session_id, cs.title
   ORDER BY cs.created_at DESC;
   ```

4. 플로우차트 작성
   - [ ] 세션 생성 흐름
   - [ ] 메시지 저장 흐름
   - [ ] 메시지 로드 흐름

**결과물**:
- 문제점 리스트 (우선순위 정렬)
- 불필요한 코드 리스트 (삭제 대상)

---

### Step 2: DB 클렌징 및 코드 정리

**목표**: 테스트 데이터 삭제, 불필요한 코드 제거

**작업**:
1. DB 클렌징
   ```sql
   DELETE FROM chat_messages;
   DELETE FROM chat_sessions;
   ```

2. Frontend 코드 정리
   - [ ] chat_session_id 생성 로직 제거
   - [ ] localStorage 저장/복원 로직 제거 (주석 아니고 완전 삭제)
   - [ ] 사용하지 않는 state 제거

3. Backend 코드 정리
   - [ ] chat_session_id 파라미터 제거
   - [ ] 사용하지 않는 함수 제거

---

### Step 3: Backend 긴급 수정

**목표**: 세션 관리 정상화

**작업**:

#### 3.1 GET /{session_id} 수정
**문제**: postgres_session_manager에서 조회 → 만료되면 404

**해결**:
```python
@router.get("/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    db: AsyncSession = Depends(get_async_db)  # ✅ chat_sessions 테이블에서 조회
):
    # ✅ DB에서 세션 조회
    query = select(ChatSession).where(ChatSession.session_id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfo(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        expires_at=(session.created_at + timedelta(hours=24)).isoformat(),
        last_activity=session.updated_at.isoformat(),
        metadata={}
    )
```

---

### Step 4: Frontend 수정

**목표**: WebSocket 연결 및 메시지 로드 안정화

**작업**:

#### 4.1 React Strict Mode 비활성화 (임시)
```javascript
// next.config.js
const nextConfig = {
  reactStrictMode: false,  // ✅ 임시로 비활성화
}
```

#### 4.2 handleWSMessage 위치 확인
- [ ] Line 112에 정의되어 있는지 확인
- [ ] WebSocket useEffect보다 위에 있는지 확인

#### 4.3 DB 메시지 로드 useEffect 확인
- [ ] sessionId && wsConnected 조건 확인
- [ ] API 호출 성공하는지 확인
- [ ] 콘솔 로그 확인

---

### Step 5: 테스트 (하나씩)

**목표**: 각 단계마다 즉시 테스트

#### 5.1 세션 생성 테스트
```
1. 브라우저 완전히 닫기
2. http://localhost:3001 열기
3. 콘솔 확인:
   ✅ "✅ New session created: session-xxx" (1번만!)
   ✅ "✅ Connected" (WebSocket)
```

#### 5.2 메시지 저장 테스트
```
1. 메시지 전송: "임대차계약 문의"
2. 백엔드 로그 확인:
   ✅ "💾 Message saved: user → session-xxx"
   ✅ "💾 Message saved: assistant → session-xxx"
3. DB 조회:
   SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 2;
```

#### 5.3 F5 새로고침 테스트
```
1. F5 누르기
2. 콘솔 확인:
   ✅ "✅ Loaded 2 messages from DB"
3. 화면 확인:
   ✅ 대화 내역 그대로 유지
```

---

## 5. 테스트 시나리오

### 시나리오 1: 완전히 새로운 사용자
```
1. 브라우저 열기
2. sessionStorage 비어있음
3. POST /start → 새 세션 생성
4. 환영 메시지 표시
5. 메시지 전송 → DB 저장
6. F5 새로고침 → DB에서 로드
```

### 시나리오 2: 돌아온 사용자
```
1. 브라우저 열기
2. sessionStorage에 이전 session_id 있음
3. GET /{session_id} → 세션 검증 성공
4. WebSocket 연결
5. DB에서 메시지 로드
6. 이어서 대화
```

### 시나리오 3: F5 새로고침
```
1. 채팅 중
2. F5 새로고침
3. sessionStorage에서 session_id 복원
4. WebSocket 재연결
5. DB에서 메시지 로드
6. 대화 내역 그대로 유지
```

---

## 6. 우선순위 및 필수 사항

### 필수 설정 (절대 잊지 말 것)

1. ✅ **POST /start에서 chat_sessions INSERT**
   - 이미 수정됨
   - 확인 필요

2. ✅ **_save_message_to_db() 호출 위치**
   - 사용자 메시지 수신 직후
   - AI 응답 생성 직후

3. ❌ **GET /{session_id}는 chat_sessions 테이블 조회**
   - 아직 수정 안 됨
   - Step 3.1에서 수정 예정

4. ⏳ **React Strict Mode는 개발 모드에서만**
   - 프로덕션에서는 1번만 실행
   - 임시로 비활성화 고려

### 우선순위

| 순위 | 작업 | 상태 |
|------|------|------|
| P0 | 세션 1개만 생성되도록 | ⏳ |
| P1 | GET /{session_id} 수정 (DB 조회) | ⏳ |
| P2 | F5 새로고침 시 메시지 로드 | ⏳ |
| P3 | chat_session_id 제거 | ⏳ |
| P4 | localStorage 완전 제거 | ⏳ |

---

## 7. 진행 상황

### Phase 0: 구조 파악 (진행 중) 🔍

- [ ] Backend 코드 읽기
- [ ] Frontend 코드 읽기
- [ ] Database 조회
- [ ] 플로우차트 작성
- [ ] 문제점 정리

### Phase 1: 클렌징 (대기) ⏳

- [ ] DB 클렌징
- [ ] Frontend 코드 정리
- [ ] Backend 코드 정리

### Phase 2: Backend 수정 (대기) ⏳

- [ ] GET /{session_id} 수정

### Phase 3: Frontend 수정 (대기) ⏳

- [ ] React Strict Mode 비활성화
- [ ] handleWSMessage 확인
- [ ] DB 로드 useEffect 확인

### Phase 4: 테스트 (대기) ⏳

- [ ] 세션 생성 테스트
- [ ] 메시지 저장 테스트
- [ ] F5 새로고침 테스트

---

**문서 끝**
