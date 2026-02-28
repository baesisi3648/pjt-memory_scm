# Memory SCM Intelligence Platform - TRD

## 1. 기술 스택

### 결정 방식
- **사용자 레벨**: L3 (경험자)
- **결정 방식**: AI 추천 + 사용자 선택 + 재검토 반영

### 1.1 프론트엔드

| 항목 | 선택 | 이유 |
|------|------|------|
| 프레임워크 | React + TypeScript | 생태계 풍부, 타입 안전성 |
| 빌드 도구 | Vite | 빠른 HMR, 경량 |
| 그래프 시각화 | Cytoscape.js | 클러스터 노드, zoom, 네트워크 그래프에 최적화 |

### 1.2 백엔드

| 항목 | 선택 | 이유 |
|------|------|------|
| 프레임워크 | FastAPI (Python) | 데이터 파이프라인 + 크롤링 + 알림에 Python 생태계 최적 |
| 실시간 | WebSocket (FastAPI 내장) | 병목 이슈 실시간 푸시 |
| 스케줄러 | APScheduler | 데이터 수집 주기적 실행 |

### 1.3 데이터베이스

| 항목 | 선택 | 이유 |
|------|------|------|
| ORM | SQLModel | FastAPI 최적화, Pydantic 통합 |
| MVP DB | SQLite | 설정 없이 빠른 시작 |
| 확장 DB | PostgreSQL | 대용량 데이터, 동시접속 |
| 마이그레이션 | Alembic | 스키마 버전 관리 |

### Decision Log

| 결정 | 대안 | 선택 이유 |
|------|------|----------|
| Cytoscape.js | D3.js, React Flow | 클러스터 노드와 네트워크 그래프에 특화, D3는 범용이라 오버엔지니어링 |
| FastAPI | Django, NestJS | 데이터 수집 파이프라인 + Python 생태계 활용 |
| SQLModel | SQLAlchemy | FastAPI 창시자가 만든 ORM, Pydantic 통합 자연스러움 |
| SQLite → PostgreSQL | 처음부터 PostgreSQL | MVP 빠른 시작, ORM 덕분에 전환 용이 |

## 2. 아키텍처

- **구조**: Monolith (MVP) → 필요시 서비스 분리
- **패턴**: Layered Architecture (API → Service → Repository)

```
┌─────────────────────────────────────────────┐
│           Frontend (React + TS)             │
│        Cytoscape.js Graph Viewer            │
├─────────────────────────────────────────────┤
│              WebSocket / REST API            │
├─────────────────────────────────────────────┤
│           Backend (FastAPI)                  │
│  ┌──────────┬──────────┬──────────────┐     │
│  │ Data     │ Alert    │ Analysis     │     │
│  │ Collector│ Engine   │ Service      │     │
│  └──────────┴──────────┴──────────────┘     │
│  ┌──────────────────────────────────────┐   │
│  │ APScheduler (Data Collection Jobs)   │   │
│  └──────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│        SQLModel + SQLite/PostgreSQL          │
└─────────────────────────────────────────────┘
```

## 3. 보안 요구사항

- **인증**: JWT 기반 로그인
- **인가**: 역할 기반 (Admin, Analyst, Viewer)

## 4. 성능 요구사항

- 대시보드 초기 로딩: 3초 이내
- 그래프 렌더링 (1000 노드): 60fps 인터랙션
- 알림 전달 지연: 5초 이내 (WebSocket)
- API 응답 시간: 500ms 이내

## 5. 개발 환경

- Node.js: 20 LTS
- Python: 3.11+
- 패키지 매니저: pnpm (프론트), uv/pip (백엔드)
