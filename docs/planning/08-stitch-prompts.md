# Memory SCM Intelligence Platform - Stitch 디자인 프롬프트

> 각 화면별로 Stitch에 입력할 프롬프트입니다.
> 디자인 시스템(05-design-system.md) 기반으로 작성되었습니다.

---

## 공통 디자인 지침 (모든 프롬프트 앞에 붙여넣기)

```
Design System:
- Font: Inter for body text, JetBrains Mono for data/numbers
- Primary color: #2563EB (Blue 600), hover: #1D4ED8
- Background: #F8FAFC (light gray), Surface: #FFFFFF
- Border: #E2E8F0, Text: #0F172A (primary), #64748B (secondary), #94A3B8 (muted)
- Status colors: Critical #DC2626 (red), Warning #F59E0B (amber), Success #16A34A (green), Info #2563EB (blue)
- Spacing: 4/8/16/24/32/48px scale
- Border radius: 8px (lg) for buttons and cards
- Desktop-first layout, minimum width 1280px
- Clean, professional, data-driven enterprise dashboard aesthetic
- No dark mode. Light theme only.
```

---

## 화면 1: 로그인 (/login)

```
Create a login page for "Memory SCM Intelligence Platform" - a semiconductor supply chain intelligence tool.

Layout:
- Centered card on a light gray (#F8FAFC) background
- Card: white (#FFFFFF), rounded-lg, shadow-lg, max-width 420px, padding 48px
- Top: Platform logo/icon + title "Memory SCM" in 24px/700 weight, subtitle "Intelligence Platform" in 14px/#64748B

Form fields:
- Email input: label "이메일" (Korean), placeholder "name@company.com", full width, border #E2E8F0, rounded-lg, height 44px, padding 12px 16px
- Password input: label "비밀번호", placeholder "••••••••", full width, same style as email, with show/hide toggle icon on right
- 16px gap between fields

Button:
- "로그인" primary button: background #2563EB, text white, full width, height 44px, rounded-lg, font 14px/600, hover #1D4ED8

Error state:
- Below form: error message area with red text #DC2626, font 12px, hidden by default

Footer:
- Bottom of card: "© 2024 Memory SCM" in 12px/#94A3B8, centered

Overall feel: Clean, minimal, professional enterprise login. No social login buttons. No "forgot password" link for MVP.
```

---

## 화면 2: 메인 대시보드 (/dashboard)

```
Create the main dashboard page for a semiconductor supply chain intelligence platform. This is the core screen showing a dynamic value chain network graph.

Layout (full viewport):
- Top bar: height 56px, white background, shadow-sm, border-bottom #E2E8F0
  - Left: "Memory SCM" logo/text in 16px/600 #0F172A
  - Right: Settings gear icon (#64748B, 20px) + User avatar circle (32px, #2563EB background with white initials)

Alert Banner (below top bar, conditionally shown):
- Full width, padding 12px 24px
- Critical alert: background #FEF2F2, left border 4px solid #DC2626, text #991B1B
  - Left: red warning triangle icon 16px
  - Text: "⚠ [Company Name] 공급 차질 감지 - 리드타임 300% 증가" in 14px/500
  - Right: "자세히 보기" link in #2563EB, "닫기" X icon in #94A3B8
- Warning alert: background #FFFBEB, left border 4px solid #F59E0B, text #92400E
- Multiple alerts stack vertically with 4px gap

Main Content (remaining viewport):
- Full-width network graph area, background #F8FAFC
- Graph visualization showing semiconductor value chain:
  - 5 cluster groups arranged left-to-right: 원자재 → 장비사 → 팹(FAB) → 패키징 → 모듈
  - Each cluster: rounded rectangle, background rgba(59, 130, 246, 0.1), dashed border #93C5FD, label on top in 12px/600 #2563EB
  - Inside each cluster: 3-8 company nodes as circles (40px diameter, fill #3B82F6, white text 11px)
  - Edges between nodes: curved lines, stroke #CBD5E1, 1.5px width, with small arrow at end
  - Alert overlay: nodes with issues have a small red warning triangle icon (16px) at top-right, node border changes to #EF4444

Bottom-left floating controls:
- Zoom controls: vertical pill shape, white background, shadow-md, rounded-lg
  - "+" button (zoom in), divider line, "−" button (zoom out), divider, "⊡" fit-all button
  - Each button: 36px square, #64748B icon, hover #F1F5F9

Bottom-right floating button:
- Filter toggle: "필터" text + funnel icon, white background, shadow-md, rounded-lg, padding 8px 16px, border #E2E8F0, text #0F172A 14px/500
  - Active state: background #2563EB, text white (when filter panel is open)

Selected node state:
- Selected node: border 3px #8B5CF6, glow effect
- Connected edges: highlighted #2563EB, 2.5px width
- Non-connected nodes: opacity 0.3

Overall feel: Clean, spacious graph visualization. The graph is the hero element taking up 90%+ of the viewport. Minimal chrome, maximum data.
```

---

## 화면 3: 사이드 패널 (노드 클릭 시 오버레이)

```
Create a slide-in side panel that appears from the right when a user clicks a node on the network graph. The panel overlays the graph (graph stays visible on the left).

Panel container:
- Width: 400px, height: 100vh (minus top bar 56px)
- Background: white, shadow-xl (shadow on left side)
- Position: fixed right, slide-in animation from right 200ms ease-out
- Overflow-y: auto with custom thin scrollbar

Panel Header:
- Padding: 24px 24px 16px
- Top row: Company name "Samsung Electronics" in 20px/600 #0F172A + country flag emoji
  - Right: X close button, 32px, #94A3B8, hover #64748B
- Second row: Cluster badge "팹(FAB)" - inline pill, background #DBEAFE, text #2563EB, 12px/500, rounded-full, padding 2px 10px
- Third row: "대한민국 · 메모리 반도체 제조" in 14px/400 #64748B

Divider: 1px #E2E8F0, margin 0 24px

Issue Summary Section:
- Padding: 16px 24px
- Section title: "이슈 요약" in 14px/600 #0F172A, with red dot indicator if active issues
- Issue card: background #FEF2F2, rounded-lg, padding 12px 16px, border-left 3px #DC2626
  - Severity badge: "Critical" pill, background #DC2626, text white, 11px/600
  - Title: "DRAM 공급 차질 - 리드타임 300% 증가" in 13px/500 #0F172A
  - Date: "2024.01.15" in 12px #94A3B8
- Warning issue card: background #FFFBEB, border-left #F59E0B, severity "Warning" in amber

Related News Section:
- Padding: 16px 24px
- Section title: "관련 뉴스" in 14px/600 #0F172A
- News list (3-5 items):
  - Each item: padding 8px 0, border-bottom 1px #F1F5F9
  - Headline: "삼성전자, 차세대 HBM4 양산 일정 확정" in 13px/400 #0F172A, hover #2563EB
  - Source + date: "Reuters · 2024.01.14" in 11px #94A3B8
  - External link icon (12px, #94A3B8) on right

Divider: 1px #E2E8F0

Relations Section:
- Padding: 16px 24px
- Two sub-sections:
  - "업스트림 (공급사)" title in 13px/600 #64748B with up-arrow icon
    - List of companies: each as a clickable row
    - Company name "SK Hynix" in 13px/500 #0F172A
    - Relation type "supplier" in 11px #94A3B8
    - Right: chevron-right icon #CBD5E1
    - Hover: background #F8FAFC
  - "다운스트림 (수요사)" title in 13px/600 #64748B with down-arrow icon
    - Same list style

Each relation link is clickable - clicking navigates the graph to focus on that company and opens a new panel for it.

Overall feel: Information-dense but well-organized. Clear visual hierarchy. Easy to scan quickly.
```

---

## 화면 4: 필터 오버레이 패널 (토글 시)

```
Create a filter overlay panel that slides in from the right side of the dashboard. It allows users to select which companies to display on the network graph.

Panel container:
- Width: 320px, max-height: 80vh
- Background: white, shadow-xl, rounded-tl-lg rounded-bl-lg
- Position: fixed right, below top bar (top: 56px)
- Overflow-y: auto with thin scrollbar
- Slide-in animation from right 200ms ease-out

Panel Header:
- Padding: 20px 20px 12px
- Title: "기업 필터" in 16px/600 #0F172A
- Right: X close button, 28px, #94A3B8
- Below title: search input
  - Full width, height 36px, border #E2E8F0, rounded-lg, padding 8px 12px
  - Left: search magnifying glass icon 16px #94A3B8
  - Placeholder: "기업명 검색..." in 13px #94A3B8

Preset Buttons Section:
- Padding: 12px 20px
- Label: "프리셋" in 12px/600 #64748B, uppercase tracking
- Horizontal row of pill buttons, wrapping:
  - "전체" - ghost style, border #E2E8F0, text #64748B, 12px/500, rounded-full, padding 4px 12px
  - "상위 100개" - same ghost style
  - "메모리 공급사" - same
  - "장비사만" - same
  - Active preset: background #2563EB, text white, border #2563EB

Divider: 1px #E2E8F0, margin 0 20px

Cluster Accordion List:
- Padding: 8px 20px
- Each cluster as an accordion:
  - Accordion header: padding 10px 0, cursor pointer
    - Left: expand/collapse chevron icon 16px #94A3B8 (rotates 90° when open)
    - Cluster name: "원자재" in 14px/500 #0F172A
    - Right: selected count badge "3/12" in 12px #94A3B8
    - Hover: background #F8FAFC rounded

  - Accordion body (expanded):
    - Company checkbox list, padding-left 24px
    - Each row: padding 6px 0
      - Checkbox: 16px, border #CBD5E1, checked: background #2563EB with white checkmark
      - Company name: "Sumco Corporation" in 13px/400 #0F172A
      - If company has alert: small red dot (6px) after name

  - Clusters in order: 원자재, 장비사, 팹(FAB), 패키징, 모듈
  - First cluster expanded by default, rest collapsed

Divider: 1px #E2E8F0

Footer (sticky bottom):
- Padding: 16px 20px
- Background: white, border-top 1px #E2E8F0
- Two buttons side by side, 8px gap:
  - "초기화" secondary button: background white, border #E2E8F0, text #64748B, 13px/500, rounded-lg, flex 1, height 36px
  - "적용" primary button: background #2563EB, text white, 13px/600, rounded-lg, flex 1, height 36px, hover #1D4ED8

Overall feel: Compact, functional filter panel. Quick to scan and select. Presets for fast filtering.
```

---

## 화면 5: 알림 설정 (/settings/alerts)

```
Create an alert settings page where users can configure alert rules for the semiconductor supply chain intelligence platform.

Layout:
- Background: #F8FAFC
- Top bar: same as dashboard (56px, "Memory SCM" logo, user avatar)
  - Add breadcrumb below logo: "대시보드 / 알림 설정" in 13px, "대시보드" as #2563EB link, "알림 설정" as #64748B text

Main Content:
- Centered container, max-width 800px, padding 32px 24px
- Page title: "알림 설정" in 24px/700 #0F172A
- Subtitle: "공급망 이상 감지 규칙을 관리합니다" in 14px/400 #64748B
- 24px gap

Alert Rules List:
- Each rule as a white card, rounded-lg, border #E2E8F0, padding 20px 24px, margin-bottom 12px
  - Top row:
    - Left: Rule name "DRAM 가격 급등 알림" in 16px/600 #0F172A
    - Right: Toggle switch (44px wide, 24px height)
      - Active: background #2563EB with white circle
      - Inactive: background #CBD5E1 with white circle
  - Second row: Rule description in 13px/400 #64748B
    - "DRAM 현물 가격이 전주 대비 15% 이상 변동 시 알림"
  - Third row: metadata tags
    - Severity pill: "Critical" background #FEF2F2 text #DC2626, or "Warning" background #FFFBEB text #92400E
    - Channel pill: "이메일" background #F1F5F9 text #64748B, "인앱" background #F1F5F9 text #64748B
    - 6px gap between pills, each pill: 11px/500, rounded-full, padding 2px 10px
  - Bottom row: "수정" text button #2563EB 13px/500 + "삭제" text button #DC2626 13px/500, 16px gap

- Show 3-4 sample rules:
  1. "DRAM 가격 급등" - Critical - 이메일, 인앱
  2. "NAND 리드타임 지연" - Warning - 인앱
  3. "신규 공급 차질 뉴스" - Info - 인앱
  4. "장비 납기 변동" - Warning - 이메일

Add Rule Button:
- Below rule list: dashed border card, rounded-lg, padding 16px, text center
  - "+" icon + "새 규칙 추가" text, #2563EB, 14px/500
  - Hover: background #F8FAFC, border-color #2563EB

Rule Editor Modal (shown when editing or adding):
- Modal overlay: background rgba(0,0,0,0.5)
- Modal card: white, rounded-lg, shadow-2xl, max-width 560px, centered
- Header: "규칙 편집" in 18px/600 #0F172A, X close button right
- Form fields (16px gap between):
  - "규칙명" text input, full width
  - "조건 유형" select dropdown: 가격 변동, 리드타임 변동, 뉴스 감지, 재고 변동
  - "임계값" number input with unit selector (%, 일, 건)
  - "심각도" radio group: Critical (red dot), Warning (amber dot), Info (blue dot)
  - "알림 채널" checkbox group: 이메일, 인앱 알림
- Footer: "취소" secondary button + "저장" primary button, right-aligned

Back Navigation:
- Top of content area: "← 대시보드로 돌아가기" link, #2563EB, 14px/500

Overall feel: Clean settings page. Easy to understand rule structure. Quick toggle on/off without editing.
```

---

## 사용 방법

1. **공통 디자인 지침**을 먼저 Stitch에 입력하거나, 각 프롬프트 상단에 붙여넣습니다
2. 화면별 프롬프트를 순서대로 입력합니다
3. 생성된 결과물을 `frontend/src/` 디렉토리에 배치합니다:
   - 화면 1 → `pages/LoginPage.tsx`
   - 화면 2 → `pages/DashboardPage.tsx`
   - 화면 3 → `components/graph/SidePanel.tsx`
   - 화면 4 → `components/graph/FilterPanel.tsx`
   - 화면 5 → `pages/AlertSettingsPage.tsx`

## 디자인 참조 키워드

Stitch에서 추가 참고할 수 있는 키워드:
- **스타일**: Enterprise SaaS dashboard, Data visualization platform, Network graph UI
- **참고 제품**: Figma, Linear, Notion, Grafana (graph 부분)
- **톤**: Professional, Clean, Data-driven, Minimal chrome
