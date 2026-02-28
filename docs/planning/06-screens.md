# Memory SCM Intelligence Platform - 화면 목록

## 화면 1: 로그인
- **ID**: screen-01
- **경로**: /login
- **기능**: 사용자 인증
- **컴포넌트**:
  - EmailInput
  - PasswordInput
  - LoginButton
  - ErrorMessage

## 화면 2: 메인 대시보드
- **ID**: screen-02
- **경로**: /dashboard
- **기능**: 밸류체인 동적 그래프 + 알림 + 필터
- **컴포넌트**:
  - AlertBanner (Critical/Warning 알림 표시)
  - ValueChainGraph (Cytoscape.js 기반 동적 그래프)
    - ClusterNode (원자재, 장비사, 팹, 패키징, 모듈 클러스터)
    - CompanyNode (개별 기업 노드)
    - RelationEdge (공급 관계 엣지)
    - AlertIcon (병목 경고 아이콘 오버레이)
    - ZoomControls (zoom in/out/fit)
  - FilterToggleButton (기업 필터 토글)
  - SettingsLink (알림 설정 이동)

## 화면 3: 사이드 패널
- **ID**: screen-03
- **경로**: 없음 (대시보드 내 오버레이)
- **기능**: 노드 상세 정보 + 이슈 + 관계 탐색
- **컴포넌트**:
  - PanelHeader (기업/클러스터명, 닫기 버튼)
  - CompanyInfo (기본 정보: 국가, 밸류체인 위치, 설명)
  - IssueSummary (병목/이슈 요약)
  - RelatedNewsList (관련 뉴스 헤드라인 3-5개)
  - RelationLinks (업스트림/다운스트림 기업 목록, 클릭 시 그래프 포커스 이동)
  - CloseButton

## 화면 4: 필터 오버레이 패널
- **ID**: screen-04
- **경로**: 없음 (대시보드 내 오버레이)
- **기능**: 표시할 기업 선택 및 필터링
- **컴포넌트**:
  - SearchInput (기업명 검색)
  - PresetSelector (상위 100개, 메모리 공급사만, 장비사만 등)
  - ClusterAccordion (클러스터별 기업 목록)
  - CompanyCheckbox (기업별 체크박스)
  - ApplyButton (필터 적용)
  - ResetButton (필터 초기화)

## 화면 5: 알림 설정
- **ID**: screen-05
- **경로**: /settings/alerts
- **기능**: 알림 규칙 커스터마이징
- **컴포넌트**:
  - AlertRuleList (현재 설정된 규칙 목록)
  - AddRuleButton (새 규칙 추가)
  - RuleEditor (규칙 편집 폼: 조건, 임계값, 알림 채널)
  - SaveButton
  - BackButton (대시보드 이동)

## 화면 간 이동

```
로그인 (/login)
    │
    ▼
메인 대시보드 (/dashboard)
    │
    ├── 노드 클릭 ──▶ 사이드 패널 (오버레이)
    │                    │
    │                    └── 링크 클릭 ──▶ 그래프 노드 포커스 이동 + 새 패널
    │
    ├── 필터 토글 ──▶ 필터 패널 (오버레이)
    │                    │
    │                    └── 적용 ──▶ 그래프 업데이트
    │
    └── 설정 ──▶ 알림 설정 (/settings/alerts)
                    │
                    └── 저장/뒤로 ──▶ 대시보드
```

## 재사용 컴포넌트

| 컴포넌트 | 사용 화면 |
|----------|----------|
| Button (Primary, Secondary, Ghost) | 전체 |
| Input (Text, Email, Password, Search) | 로그인, 필터, 설정 |
| AlertBanner | 대시보드 |
| Panel (Side, Overlay) | 사이드 패널, 필터 패널 |
| Checkbox | 필터 패널 |
| Accordion | 필터 패널 |
