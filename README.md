# Octo Chatbot

LangGraph 1.0 Supervisor Pattern을 사용한 멀티 에이전트 챗봇 시스템

## 기술 스택

- **LangChain 1.0**: LLM 애플리케이션 프레임워크
- **LangGraph 1.0**: 상태 기반 멀티 에이전트 오케스트레이션
- **FastAPI**: 비동기 웹 프레임워크
- **PostgreSQL**: 체크포인트 및 데이터 저장
- **FAISS/ChromaDB**: 벡터 데이터베이스

## 설치

```bash
# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 등을 설정
```

## 실행

```bash
# 개발 서버 실행
uv run uvicorn backend.app.main:app --reload
```

## 아키텍처

Supervisor 패턴을 사용한 계층적 멀티 에이전트 시스템:
- **Supervisor**: 메인 그래프, 작업 분배 및 응답 조율
- **Base Agent**: 일반 질의응답
- **RAG Agent**: 문서 검색 및 답변
- **Search Agent**: 웹 검색 기반 답변

## 개발 상태

Phase 0: 환경 설정 완료
Phase 1: Supervisor 기본 구조 개발 예정
# octostrator
