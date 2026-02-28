# Memory SCM - 개선 로드맵

> 42개 개선 포인트 | 95% 무료 | 5단계 우선순위

---

## 1. 무료/저비용 API 연동

| # | API | 용도 | 비용 | 난이도 | 우선순위 |
|---|-----|------|------|--------|----------|
| 1.1 | **Yahoo Finance** (`yfinance`) | 반도체 기업 주가/시가총액 실시간 조회 | 무료 | Low | **HIGH** |
| 1.2 | **FRED API** (미연준 경제데이터) | 반도체 관련 매크로 지표 (ISM PMI, 산업생산지수) | 무료 | Low | MEDIUM |
| 1.3 | **frankfurter.app** (환율) | KRW/USD, JPY/USD, TWD/USD 실시간 환율 | 무료 | Low | MEDIUM |
| 1.4 | **GDELT Project** | 지정학적 이벤트 모니터링 (미중 반도체 규제, 대만 리스크) | 무료 | Medium | **HIGH** |
| 1.5 | **SEC EDGAR** | 미국 반도체 기업 10-K/10-Q/8-K 공시 | 무료 | Medium | LOW |
| 1.6 | **DART API** (금감원) | 삼성전자, SK하이닉스 분기보고서/사업보고서 | 무료 | Medium | MEDIUM |
| 1.7 | **RSS Feed 수집기** | SemiWiki, EE Times 등 반도체 전문매체 직접 수집 | 무료 | Low | **HIGH** |
| 1.8 | **Google Trends** (`pytrends`) | "DRAM 가격", "HBM", "AI 칩" 등 검색 트렌드 | 무료 | Low | LOW |

### 상세 설명

**1.1 Yahoo Finance** - API 키 불필요. `pip install yfinance`로 바로 사용. 삼성(005930.KS), SK하이닉스(000660.KS), Micron(MU), TSMC(TSM), ASML(ASML) 등의 주가를 SidePanel에 미니 스파크라인 차트로 표시. 주가 급락은 공급망 이슈의 선행지표.

**1.4 GDELT** - 미중 칩 수출규제, 일본-한국 무역분쟁, 대만해협 긴장 등 지정학 이벤트를 구조화된 데이터로 제공. 뉴스 헤드라인보다 훨씬 풍부한 이벤트 메타데이터(who, what, where, when).

**1.7 RSS Feed** - NewsAPI 무료티어는 일 100건 제한 + 최근 1개월만 조회 가능. RSS는 무제한 무료이며 반도체 전문매체에서 더 관련성 높은 기사 수집 가능. `feedparser` 라이브러리 사용.

---

## 2. 미구현 핵심 기능 (Critical Gap)

| # | 기능 | 현재 상태 | 난이도 | 우선순위 |
|---|------|-----------|--------|----------|
| 2.1 | **데이터 수집 파이프라인** | DataSource/DataPoint 모델만 존재, 스케줄러 미구현 | Medium | **CRITICAL** |
| 2.2 | **이상 탐지 엔진** | AlertRule CRUD 있으나 실제 평가 엔진 없음 | High | **CRITICAL** |
| 2.3 | **WebSocket 실시간 푸시** | TRD에 5초 이내 알림 요구사항 있으나 미구현 | Medium | MEDIUM |
| 2.4 | **DataPoint API 엔드포인트** | 모델만 존재, API 없음 | Low | **HIGH** |
| 2.5 | **가격/재고 대시보드 카드** | PRD Phase 2로 연기됨 | Medium | **HIGH** |
| 2.6 | **기업 로고** | SidePanel에 이니셜만 표시 | Low | LOW |
| 2.7 | **글로벌 검색** | 필터패널 내 검색만 존재 | Low | MEDIUM |
| 2.8 | **리포트 내보내기** | PRD Phase 2 (CSV/PDF) | Medium | LOW |

### 상세 설명

**2.1 데이터 수집 파이프라인** - TRD에 APScheduler 명시되어 있으나 구현 없음. 외부 API에서 주기적으로 데이터를 수집하여 DataPoint 테이블에 저장하는 백그라운드 작업이 필요. 이것 없이는 플랫폼 전체가 정적 시드 데이터로만 운영됨.

**2.2 이상 탐지 엔진** - PRD의 핵심 가치 제안. "SCM 매니저의 아침 첫 행동은 '어디에 문제가 있나?'를 확인하는 것." AlertRule은 CRUD 가능하지만 실제로 DataPoint를 평가하여 Alert를 생성하는 엔진이 없음. `price_change`, `lead_time`, `news_detect`, `inventory_change` 4가지 룰 타입 지원 필요.

**2.4 DataPoint API** - `GET /api/v1/companies/{id}/data-points?metric=price&from=2024-01-01` 같은 엔드포인트. 가격 추이 차트, 리드타임 트렌드, 재고 수준 표시에 필수.

---

## 3. 코드 품질 / 기술 부채

| # | 이슈 | 위치 | 난이도 | 우선순위 |
|---|------|------|--------|----------|
| 3.1 | **API 키 하드코딩** | `config.py` - NEWS_API_KEY, SECRET_KEY | Low | **HIGH** |
| 3.2 | **SQLite 한계** (JSON 문자열 저장) | AlertRule.condition, UserFilter.company_ids 등 | Medium | MEDIUM |
| 3.3 | **페이지네이션 없음** | 모든 list 엔드포인트가 전체 레코드 반환 | Low | MEDIUM |
| 3.4 | **구조화된 로깅 없음** | 백엔드에 logging 없음, 에러 무시됨 | Low | **HIGH** |
| 3.5 | **datetime.utcnow() 사용** | Python 3.12+ deprecated | Low | LOW |
| 3.6 | **N+1 쿼리** | `relations.py` - 루프 내 session.get() | Low | MEDIUM |
| 3.7 | **불필요한 setInterval** | `ValueChainGraph.tsx` - 줌 라벨 500ms 폴링 | Low | LOW |
| 3.8 | **API Rate Limiting 없음** | 로그인 브루트포스 취약 | Low | MEDIUM |
| 3.9 | **프론트엔드 에러 처리 부재** | FilterPanel에서 save/delete 실패 시 무반응 | Low | MEDIUM |

### 상세 설명

**3.1 API 키 하드코딩** - `NEWS_API_KEY`가 소스코드에 직접 포함. `.env` 파일로 이동하고 기본값을 빈 문자열로 변경 필요. `SECRET_KEY`도 `"change-me-in-production"` 상태.

**3.4 구조화된 로깅** - `news_service.py`의 `except (httpx.HTTPError, Exception): return []`처럼 에러를 무시하는 패턴이 있음. 이상 탐지 엔진이나 데이터 수집 파이프라인이 실패해도 알 방법이 없음. Python `structlog` 또는 표준 `logging` 모듈 도입 필요.

---

## 4. 데이터 고도화

| # | 기능 | 용도 | 난이도 | 우선순위 |
|---|------|------|--------|----------|
| 4.1 | **뉴스 감성 분석** | FinBERT/TextBlob으로 뉴스 감성 점수화 | Medium | MEDIUM |
| 4.2 | **기업 리스크 스코어** | 알림수+감성+주가+지정학 복합 점수 | Medium | **HIGH** |
| 4.3 | **공급망 집중도 지수** | 티어별 HHI(허핀달-허쉬만) 집중도 계산 | Low | MEDIUM |
| 4.4 | **리드타임 추적** | 장비 납기 (ASML EUV: 18-24개월 등) | Medium | **HIGH** |
| 4.5 | **가동률 데이터** | FAB 가동률 (80%↓=과잉, 95%↑=부족) | Medium | **HIGH** |

### 상세 설명

**4.2 리스크 스코어** - 기업별 복합 리스크 점수 = 활성 알림 수/심각도 + 부정 뉴스 감성 + 주가 변동 + 공급망 집중도 + 지정학적 노출도. SidePanel 헤더에 리스크 게이지 표시, 그래프 노드 색상/크기에 반영.

**4.4 리드타임** - AlertSettingsPage에 이미 `lead_time` 조건 타입이 정의되어 있으나 데이터 피드 없음. 초기에는 수동 입력, 이후 공시자료 크롤링으로 자동화.

---

## 5. UI/UX 개선

| # | 기능 | 현재 상태 | 난이도 | 우선순위 |
|---|------|-----------|--------|----------|
| 5.1 | **노드 크기 차등화** | 모든 기업 동일 크기 (34px) | Low | MEDIUM |
| 5.2 | **엣지 두께 = 관계 강도** | strength 필드 있으나 고정 width: 1.5 | Low | MEDIUM |
| 5.3 | **Toast 알림 시스템** | 에러/성공 피드백 없음 | Low | **HIGH** |
| 5.4 | **다크 모드** | TopBar만 다크, 본문은 라이트 | Medium | LOW |
| 5.5 | **SidePanel 탭 인터페이스** | 전체 섹션 단일 스크롤 | Low | MEDIUM |
| 5.6 | **그래프 미니맵** | 줌인 시 전체 맥락 상실 | Low | MEDIUM |
| 5.7 | **자동 레이아웃** (dagre) | 수동 preset 레이아웃, 기업 많으면 겹침 | Medium | MEDIUM |
| 5.8 | **키보드 네비게이션** | 마우스만 지원 | Medium | LOW |
| 5.9 | **모바일 반응형** | 고정 레이아웃, 모바일 미지원 | Medium | LOW |

---

## 6. 성능 최적화

| # | 기능 | 현재 상태 | 난이도 | 우선순위 |
|---|------|-----------|--------|----------|
| 6.1 | **백엔드 응답 캐싱** | 캐싱 없음 (뉴스 DB 캐시 제외) | Medium | **HIGH** |
| 6.2 | **React Query** (TanStack) | 수동 useState/useEffect 데이터 페칭 | Medium | **HIGH** |
| 6.3 | **통합 그래프 데이터 API** | 대시보드 로드 시 4개 API 호출 | Low | MEDIUM |
| 6.4 | **Cytoscape 증분 업데이트** | 전체 elements 순회 방식 | Medium | LOW |
| 6.5 | **가상 스크롤** | SidePanel 리스트 전체 렌더링 | Low | LOW |

### 상세 설명

**6.1 백엔드 캐싱** - MVP: `cachetools.TTLCache`로 인메모리 캐싱 (인프라 불필요). 프로덕션: Redis. 기업/클러스터/관계 데이터는 거의 변하지 않으므로 캐싱 효과 큼.

**6.2 React Query** - 자동 캐싱, 백그라운드 리페치, stale-while-revalidate, 재시도 로직, 요청 중복 제거. SidePanel에서 기업 간 전환 시 즉시 응답 가능.

---

## 7. 인프라 개선

| # | 기능 | 현재 상태 | 난이도 | 우선순위 |
|---|------|-----------|--------|----------|
| 7.1 | **백그라운드 잡 시스템** | 스케줄러 미구현 (TRD에 APScheduler 명시) | Medium | **CRITICAL** |
| 7.2 | **Alembic 마이그레이션** | create_all() 직접 호출, 마이그레이션 없음 | Low | **HIGH** |
| 7.3 | **Docker Compose** | 로컬 직접 실행만 가능 | Low | MEDIUM |
| 7.4 | **API 버저닝 전략** | /api/v1/ 프리픽스만 존재 | Low | LOW |
| 7.5 | **헬스체크 강화** | `{"status": "ok"}`만 반환 | Low | MEDIUM |
| 7.6 | **환경별 설정** | dev/staging/prod 구분 없음 | Low | MEDIUM |
| 7.7 | **프론트엔드 env 변수** | API URL 하드코딩 | Low | LOW |
| 7.8 | **테스트 인프라** | 백엔드 71개 테스트 있으나 CI 미연동 | Medium | **HIGH** |

---

## 구현 로드맵 (추천 순서)

### Phase 1: 기반 정비 (1-2주)

| 순서 | 항목 | 참조 |
|------|------|------|
| 1 | API 키 .env 이동 | 3.1 |
| 2 | 구조화된 로깅 도입 | 3.4 |
| 3 | Toast 알림 시스템 | 5.3 |
| 4 | Alembic 마이그레이션 설정 | 7.2 |
| 5 | N+1 쿼리 수정 | 3.6 |
| 6 | setInterval 제거 | 3.7 |
| 7 | datetime.utcnow 교체 | 3.5 |

### Phase 2: 핵심 엔진 (2-4주)

| 순서 | 항목 | 참조 |
|------|------|------|
| 8 | APScheduler 파이프라인 | 2.1 + 7.1 |
| 9 | 이상 탐지 엔진 | 2.2 |
| 10 | DataPoint API | 2.4 |
| 11 | Yahoo Finance 연동 | 1.1 |
| 12 | RSS Feed 수집기 | 1.7 |
| 13 | 페이지네이션 추가 | 3.3 |

### Phase 3: 데이터 고도화 (2-3주)

| 순서 | 항목 | 참조 |
|------|------|------|
| 14 | GDELT 지정학 모니터링 | 1.4 |
| 15 | FRED 매크로 지표 | 1.2 |
| 16 | 환율 추적 | 1.3 |
| 17 | 뉴스 감성 분석 | 4.1 |
| 18 | 기업 리스크 스코어 | 4.2 |

### Phase 4: UX 고도화 (1-2주)

| 순서 | 항목 | 참조 |
|------|------|------|
| 19 | React Query 전환 | 6.2 |
| 20 | 엣지 두께 차등화 | 5.2 |
| 21 | 노드 크기 차등화 | 5.1 |
| 22 | SidePanel 탭 | 5.5 |
| 23 | 그래프 미니맵 | 5.6 |
| 24 | 백엔드 캐싱 | 6.1 |

### Phase 5: 프로덕션 준비 (1-2주)

| 순서 | 항목 | 참조 |
|------|------|------|
| 25 | WebSocket 실시간 알림 | 2.3 |
| 26 | Docker Compose | 7.3 |
| 27 | PostgreSQL 전환 | 3.2 |
| 28 | Rate Limiting | 3.8 |
| 29 | 헬스체크 강화 | 7.5 |
| 30 | 테스트 CI 연동 | 7.8 |

---

## 요약 통계

- **총 개선 포인트**: 42개
- **무료**: 40개 (95%)
- **저비용**: 2개 (5%) - PostgreSQL Docker, Redis
- **CRITICAL 우선순위**: 3개 (데이터 파이프라인, 이상 탐지, 백그라운드 잡)
- **HIGH 우선순위**: 12개
- **전체 예상 기간**: 약 8-13주 (5 Phase)
- **예상 비용**: 사실상 $0 (전부 무료 티어 또는 오픈소스)
