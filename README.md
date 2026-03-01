# Memory SCM Intelligence Platform

메모리 반도체 공급망 데이터를 수집·시각화·분석하여 실시간 인사이트를 제공하는 인텔리전스 플랫폼

## 주요 기능

- **밸류체인 동적 그래프** — 원자재 → 장비 → FAB → 패키징 → 모듈 5단계 공급망을 Cytoscape.js 인터랙티브 네트워크로 시각화
- **이상 감지 & 알림** — 가격 변동, 리드타임 지연, 뉴스 감지, 재고 변동 등 규칙 기반 자동 알림
- **기업 드릴다운 분석** — 노드 클릭 시 사이드 패널에서 이슈 요약, 관련 뉴스, 업/다운스트림 관계 탐색
- **다중 데이터 소스** — Yahoo Finance, FRED, GDELT, SEC EDGAR, DART, RSS, Google Trends 등 8개 무료 API 연동
- **실시간 업데이트** — WebSocket 기반 알림 푸시, APScheduler 주기적 데이터 수집

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS v4 · Cytoscape.js · Zustand · TanStack Query |
| Backend | FastAPI · Python 3.11+ · SQLModel · Alembic · APScheduler |
| Database | SQLite (MVP) |
| Auth | JWT (python-jose + passlib) |
| CI | GitHub Actions (ruff lint + pytest + vite build) |

## 프로젝트 구조

```
├── frontend/                  # React SPA
│   ├── src/
│   │   ├── components/        # UI 컴포넌트 (12개)
│   │   │   ├── alerts/        # 알림 규칙 편집 모달
│   │   │   ├── dashboard/     # 대시보드 메트릭 카드
│   │   │   ├── graph/         # 밸류체인 그래프, 사이드패널, 필터
│   │   │   ├── layout/        # TopBar, AuthGuard, GlobalSearch
│   │   │   └── ui/            # Button, Input, Toast, AlertBanner
│   │   ├── hooks/             # useCytoscape, useWebSocket
│   │   ├── pages/             # Dashboard, AlertSettings, Login
│   │   ├── services/          # API 클라이언트 (axios)
│   │   ├── stores/            # Zustand (auth, toast)
│   │   └── types/             # TypeScript 타입 정의
│   └── public/logos/           # 기업 로고 30개
│
├── backend/                   # FastAPI API 서버
│   ├── app/
│   │   ├── api/               # 24개 라우터 모듈
│   │   ├── models/            # SQLModel 모델 (10개 테이블)
│   │   ├── schemas/           # Pydantic 요청/응답 스키마
│   │   ├── services/          # 비즈니스 로직 (15개 서비스)
│   │   └── core/              # 설정, 보안, DB, 스케줄러, 캐시
│   ├── migrations/            # Alembic 마이그레이션
│   ├── scripts/seed.py        # 시드 데이터 (30개 기업, 37개 관계)
│   └── tests/                 # pytest 테스트 (19개 모듈)
│
├── docs/planning/             # 기획 문서
│   ├── 00-neurion-proposal.md # 브레인스토밍 기획안
│   ├── 01-prd.md              # 제품 요구사항
│   ├── 02-trd.md              # 기술 요구사항
│   ├── 03-user-flow.md        # 사용자 플로우
│   ├── 04-database-design.md  # DB 설계
│   ├── 05-design-system.md    # 디자인 시스템
│   ├── 06-screens.md          # 화면 목록
│   ├── 06-tasks.md            # 태스크 분해
│   ├── 07-coding-convention.md# 코딩 컨벤션
│   ├── 08-improvements.md     # 개선 로드맵 (42개 중 40개 완료)
│   └── 08-stitch-prompts.md   # UI 디자인 프롬프트
│
└── specs/                     # YAML 명세
    ├── domain/resources.yaml
    ├── screens/               # 화면별 명세
    └── shared/                # 공유 컴포넌트/타입
```

## 시작하기

### 사전 요구사항

- Node.js 20+
- Python 3.11+

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 환경변수 설정
cp .env.example .env           # SECRET_KEY, DART_API_KEY 등 설정

# DB 초기화 & 시드 데이터
alembic upgrade head
python scripts/seed.py

# 서버 실행
uvicorn app.main:app --reload  # http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install

# 환경변수 설정
cp .env.example .env           # VITE_API_BASE_URL 설정

# 개발 서버 실행
npm run dev                    # http://localhost:5173
```

### 테스트 계정

시드 데이터에 포함된 기본 계정:
- Email: `admin@memoryscm.com`
- Password: `admin1234`

## API 엔드포인트

| 그룹 | 엔드포인트 | 설명 |
|------|-----------|------|
| Auth | `POST /api/v1/auth/login` | JWT 로그인 |
| Dashboard | `GET /api/v1/dashboard` | 통합 대시보드 데이터 |
| Companies | `GET /api/v1/companies` | 기업 목록/상세 |
| Clusters | `GET /api/v1/clusters` | 클러스터 목록 |
| Relations | `GET /api/v1/relations` | 공급망 관계 |
| Alerts | `GET /api/v1/alerts` | 알림 목록 |
| Alert Rules | `GET/POST/PUT/DELETE /api/v1/alert-rules` | 알림 규칙 CRUD |
| News | `GET /api/v1/companies/{id}/news` | 기업별 뉴스 |
| Stock | `GET /api/v1/companies/{id}/stock` | 주가 (Yahoo Finance) |
| Risk | `GET /api/v1/risk-scores` | 리스크 스코어 |
| Sentiment | `GET /api/v1/sentiment` | 뉴스 감성 분석 |
| Trends | `GET /api/v1/trends` | Google Trends |
| GDELT | `GET /api/v1/geopolitical-events` | 지정학 이벤트 |
| Exchange | `GET /api/v1/exchange-rates` | 환율 |
| FRED | `GET /api/v1/macro-indicators` | 매크로 지표 |
| Export | `GET /api/v1/export/csv`, `/pdf` | 리포트 내보내기 |
| WebSocket | `WS /api/v1/ws` | 실시간 알림 |
| Health | `GET /api/v1/health` | 헬스체크 |

## 밸류체인 기업 (30개)

| Tier | 기업 |
|------|------|
| 원자재 | SK Materials, Soulbrain, DNF, Hansol Chemical, SUMCO, Shin-Etsu Chemical |
| 장비 | ASML, Applied Materials, Lam Research, Tokyo Electron, SEMES, PSK |
| FAB | Samsung Electronics, SK hynix, Micron, TSMC, Intel, Kioxia |
| 패키징 | ASE Group, Amkor, JCET, NEPES, SFA Semicon, Hana Micron |
| 모듈 | Samsung SDI, SK Nexilis, LG Innotek, Innox, BH, Daeduck Electronics |

## 테스트

```bash
# Backend
cd backend
pytest tests/ -v

# Frontend
cd frontend
npm run build          # TypeScript 타입 체크 + 빌드
npm run lint           # ESLint
```

## 라이선스

Private
