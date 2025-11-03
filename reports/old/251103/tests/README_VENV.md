# 가상환경 사용 가이드

## ✅ 가상환경 설정 완료

가상환경이 성공적으로 생성되고 모든 패키지가 설치되었습니다!

**위치:** `C:\kdy\projects\holmesnayangs\bera_v001\holmesnyangz\venv`

## 🚀 빠른 시작

### 1. 가상환경 활성화

**Windows (CMD):**
```cmd
cd C:\kdy\projects\holmesnayangs\bera_v001\holmesnyangz
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
cd C:\kdy\projects\holmesnayangs\bera_v001\holmesnyangz
venv\Scripts\Activate.ps1
```

활성화되면 프롬프트 앞에 `(venv)`가 표시됩니다:
```
(venv) C:\kdy\projects\holmesnayangs\bera_v001\holmesnyangz>
```

### 2. 에이전트 테스트 실행

**간단한 테스트 (권장):**
```bash
cd backend
python app/service_agent/hn_agent_simple_test.py
```

**배치 모드:**
```bash
python app/service_agent/hn_agent_simple_test.py "전세금 5% 인상" "계약 갱신"
```

### 3. 가상환경 비활성화

```bash
deactivate
```

## 📦 설치된 주요 패키지

- **LangGraph:** 0.6.7 (팀 기반 에이전트 시스템)
- **LangChain:** 0.3.27 (LLM 통합)
- **ChromaDB:** 1.1.0 (벡터 데이터베이스)
- **Sentence Transformers:** 5.1.1 (임베딩 모델)
- **PyTorch:** 2.8.0 (딥러닝 프레임워크)
- **FastAPI:** 0.115.0 (웹 프레임워크)

전체 패키지 목록:
```bash
venv\Scripts\pip.exe list
```

## 🧪 테스트 결과 확인

테스트 실행 후 다음 파일들이 생성됩니다:

- **검색 결과:** `search_result_YYYYMMDD_HHMMSS.json`
- **로그 파일:** `hn_agent_test.log`

## 🔧 venv 없이 실행 (고급 사용자)

가상환경을 활성화하지 않고 직접 실행:

```bash
cd backend
..\venv\Scripts\python.exe app\service_agent\hn_agent_simple_test.py "쿼리"
```

## 📝 대화형 모드 사용법

```bash
cd backend
python app/service_agent/hn_agent_simple_test.py
```

사용 가능한 명령어:
```
Query > 전세금 5% 인상          # 쿼리 입력
Query > legal                  # 법률 검색만
Query > real_estate            # 부동산 검색만
Query > loan                   # 대출 검색만
Query > all                    # 전체 검색
Query > quit                   # 종료
```

## 🎯 실제 테스트 결과 예시

```
[Results Summary]
  Total Results: 10
  Sources Used: ['legal_db']

[Legal Results] (10 items)
  [1] 임대차 보호 95조항
      Title:
      Relevance: 1.000
      Content: 전세금: 계약금+중도금+잔금 입니다...

  [2] 공동주택 관리에 관한 법률 제1조
      Title: 목적
      Relevance: 1.000
      Content: 제1조(목적) 이 법은 2021년 1월 1일부터 시행한다...
```

## 📂 프로젝트 구조

```
holmesnyangz/
├── venv/                          # 가상환경 (이미 생성됨)
│   ├── Scripts/
│   │   ├── python.exe
│   │   ├── pip.exe
│   │   └── activate
│   └── Lib/
├── backend/
│   └── app/
│       └── service_agent/
│           ├── hn_agent_simple_test.py    # 간단한 테스트
│           ├── hn_agent_query_test.py     # 전체 시스템 테스트
│           └── ...
├── requirements.txt               # 패키지 목록
└── README_VENV.md                # 이 파일
```

## 🐛 문제 해결

### ChromaDB 오류
```
ModuleNotFoundError: No module named 'chromadb'
```
→ 가상환경을 활성화했는지 확인하세요.

### 임베딩 모델 오류
```
Embedding model not found
```
→ 이미 수정되었습니다. `service_agent/models/KURE_v1` 경로 사용 중.

### 한글 깨짐
→ 정상입니다. 콘솔 인코딩 문제이며 JSON 파일은 정상적으로 UTF-8로 저장됩니다.

## 🔄 패키지 업데이트

새 패키지 추가:
```bash
venv\Scripts\pip.exe install <package_name>
```

requirements.txt 업데이트:
```bash
venv\Scripts\pip.exe freeze > requirements.txt
```

## 💡 팁

1. **가상환경은 항상 활성화한 상태에서 작업하세요**
2. **테스트 결과는 JSON 파일로 저장되어 나중에 확인 가능합니다**
3. **로그 파일(`hn_agent_test.log`)에서 상세 정보 확인 가능합니다**
4. **대화형 모드는 여러 쿼리를 테스트할 때 편리합니다**

---

**생성일:** 2025-10-02
**Python 버전:** 3.10
**가상환경:** venv (성공적으로 설정됨)
